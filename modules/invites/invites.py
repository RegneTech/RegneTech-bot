# modules/invites/invites.py
import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import asyncio

class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache: Dict[int, Dict[str, discord.Invite]] = {}
        self.db_path = 'invites.db'
        print("🔧 Inicializando módulo de invitaciones...")
        self.init_database()
    
    def init_database(self):
        """Inicializar la base de datos SQLite con estructura mejorada"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla principal de invitaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    invited_by_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    invite_code TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Índices para mejor rendimiento
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_invites_user_id ON invites(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_invites_invited_by_id ON invites(invited_by_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_invites_guild_id ON invites(guild_id)')
            
            conn.commit()
            conn.close()
            print("📊 Base de datos inicializada correctamente")
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Cargar cache cuando el bot esté listo"""
        print("🔄 Cargando cache de invitaciones...")
        await asyncio.sleep(3)  # Esperar un poco más para asegurar que el bot esté listo
        
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {invite.code: invite for invite in invites}
                print(f"✅ Cache cargado para {guild.name}: {len(invites)} invitaciones")
                
                # Debug: mostrar algunas invitaciones
                for invite in invites[:3]:  # Mostrar máximo 3
                    print(f"   - {invite.code}: {invite.inviter.name if invite.inviter else 'Desconocido'} ({invite.uses} usos)")
                    
            except discord.Forbidden:
                print(f"⚠️ Sin permisos para invitaciones en {guild.name}")
            except Exception as e:
                print(f"❌ Error cargando cache para {guild.name}: {e}")
        
        print("🎉 Sistema de invitaciones completamente inicializado")
        
        # Verificar que el cache se cargó correctamente
        total_cached = sum(len(invites) for invites in self.invite_cache.values())
        print(f"📊 Total de invitaciones en cache: {total_cached}")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Actualizar cache cuando se crea una nueva invitación"""
        try:
            if invite.guild.id not in self.invite_cache:
                self.invite_cache[invite.guild.id] = {}
            
            self.invite_cache[invite.guild.id][invite.code] = invite
            print(f"➕ Nueva invitación agregada al cache: {invite.code} por {invite.inviter}")
        except Exception as e:
            print(f"❌ Error agregando invitación al cache: {e}")
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Actualizar cache cuando se elimina una invitación"""
        try:
            if invite.guild.id in self.invite_cache:
                self.invite_cache[invite.guild.id].pop(invite.code, None)
                print(f"➖ Invitación eliminada del cache: {invite.code}")
        except Exception as e:
            print(f"❌ Error eliminando invitación del cache: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Detectar quién invitó al nuevo miembro"""
        guild = member.guild
        print(f"👋 {member.display_name} se unió a {guild.name}")
        
        # Evitar procesar bots
        if member.bot:
            print(f"🤖 {member.display_name} es un bot, ignorando...")
            return
        
        try:
            inviter_id = None
            used_invite_code = None
            
            # Verificar si tenemos cache para este servidor
            if guild.id not in self.invite_cache:
                print(f"⚠️ No hay cache para {guild.name}, inicializando...")
                try:
                    invites = await guild.invites()
                    self.invite_cache[guild.id] = {invite.code: invite for invite in invites}
                    print(f"🔄 Cache inicializado con {len(invites)} invitaciones")
                except discord.Forbidden:
                    print(f"❌ Sin permisos para obtener invitaciones en {guild.name}")
                    return
            
            # Obtener invitaciones actuales
            try:
                current_invites = await guild.invites()
                print(f"📊 Invitaciones actuales: {len(current_invites)}")
            except discord.Forbidden:
                print(f"❌ Sin permisos para ver invitaciones en {guild.name}")
                return
            
            cached_invites = self.invite_cache.get(guild.id, {})
            print(f"🧠 Invitaciones en cache: {len(cached_invites)}")
            
            # Método 1: Comparar con cache (método principal)
            if cached_invites:
                for invite in current_invites:
                    # Filtrar bots (como DISBOARD)
                    if invite.inviter and invite.inviter.bot:
                        print(f"🤖 Ignorando invitación de bot: {invite.inviter.name}")
                        continue
                    
                    print(f"🔍 Revisando invitación {invite.code}: {invite.uses} usos")
                    
                    if invite.code in cached_invites:
                        cached_invite = cached_invites[invite.code]
                        print(f"📋 Cache para {invite.code}: {cached_invite.uses} usos anteriores")
                        
                        if invite.uses > cached_invite.uses:
                            inviter_id = invite.inviter.id if invite.inviter else None
                            used_invite_code = invite.code
                            print(f"✅ ¡INVITADOR DETECTADO! {invite.inviter} (código: {invite.code})")
                            print(f"📈 Usos: {cached_invite.uses} → {invite.uses}")
                            break
                    else:
                        # Invitación nueva que no estaba en cache
                        if invite.uses > 0 and invite.inviter and not invite.inviter.bot:
                            inviter_id = invite.inviter.id if invite.inviter else None
                            used_invite_code = invite.code
                            print(f"🆕 Nueva invitación usada: {invite.inviter} (código: {invite.code})")
                            break
            
            # Método 2: Fallback - buscar por invitaciones recientes (si no se encontró en cache)
            if not inviter_id:
                print("🔍 Método fallback: buscando por invitaciones más probables...")
                # Buscar invitaciones que no sean de bots y tengan usos recientes
                non_bot_invites = [inv for inv in current_invites if inv.inviter and not inv.inviter.bot and inv.uses > 0]
                
                if non_bot_invites:
                    # Si solo hay una invitación de usuario real con usos, probablemente sea esa
                    if len(non_bot_invites) == 1:
                        invite = non_bot_invites[0]
                        inviter_id = invite.inviter.id
                        used_invite_code = invite.code
                        print(f"🎯 Invitador detectado por eliminación: {invite.inviter} ({invite.uses} usos)")
                    else:
                        # Si hay múltiples, tomar la que tenga menos usos (más probable que sea la reciente)
                        invite = min(non_bot_invites, key=lambda x: x.uses)
                        if invite.uses <= 5:  # Solo si tiene pocos usos (más probable que sea reciente)
                            inviter_id = invite.inviter.id
                            used_invite_code = invite.code
                            print(f"🎯 Invitador probable: {invite.inviter} ({invite.uses} usos)")
            
            # Guardar en base de datos si se encontró invitador
            if inviter_id and inviter_id != member.id:
                print(f"💾 Guardando invitación: {member.id} invitado por {inviter_id}")
                self.save_invitation(member.id, inviter_id, guild.id, used_invite_code)
                
                # Enviar mensaje al canal específico
                channel_id = 1400106792821981249  # Cambiar por el ID de tu canal
                channel = self.bot.get_channel(channel_id)
                
                if channel and channel.guild == guild:
                    inviter = guild.get_member(inviter_id)
                    if inviter:
                        print(f"📨 Enviando mensaje de bienvenida...")
                        await self.send_welcome_message(channel, member, inviter, guild)
                    else:
                        print(f"⚠️ Invitador {inviter_id} no encontrado en el servidor")
                else:
                    print(f"⚠️ Canal {channel_id} no encontrado o no es del mismo servidor")
            else:
                print(f"⚠️ No se pudo determinar el invitador para {member.display_name}")
                if not inviter_id:
                    print("   - Razón: No se detectó ningún invitador válido")
                elif inviter_id == member.id:
                    print("   - Razón: El invitador es el mismo usuario (imposible)")
            
            # Actualizar cache SIEMPRE
            print(f"🔄 Actualizando cache con {len(current_invites)} invitaciones")
            self.invite_cache[guild.id] = {invite.code: invite for invite in current_invites}
            
            # Debug: verificar que se guardó el cache
            new_cache_size = len(self.invite_cache.get(guild.id, {}))
            print(f"✅ Cache actualizado: {new_cache_size} invitaciones")
            
        except discord.Forbidden:
            print(f"❌ Sin permisos para ver invitaciones en {guild.name}")
        except Exception as e:
            print(f"❌ Error procesando member_join: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_welcome_message(self, channel: discord.TextChannel, member: discord.Member, 
                                 inviter: discord.Member, guild: discord.Guild):
        """Enviar mensaje de bienvenida personalizado"""
        try:
            # Contar invitaciones del invitador
            invite_count = self.get_user_invites_count(inviter.id, guild.id)
            
            # Mensaje principal personalizado
            description = f"{member.mention} ha sido invitado por {inviter.mention} el cual ahora tiene **{invite_count}** invitaciones"
            
            embed = discord.Embed(
                description=description,
                color=0x00ff88,
                timestamp=datetime.utcnow()
            )
            
            # Imagen del usuario que se unió
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Footer personalizado con logo del servidor
            footer_text = f"Sistema de invitaciones • {guild.name}"
            embed.set_footer(
                text=footer_text,
                icon_url=guild.icon.url if guild.icon else None
            )
            
            await channel.send(embed=embed)
            print(f"📨 Mensaje de bienvenida enviado para {member.display_name}")
            
        except Exception as e:
            print(f"❌ Error enviando mensaje de bienvenida: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Manejar cuando un miembro sale del servidor"""
        if member.bot:
            return
            
        try:
            # Marcar invitaciones como inactivas en lugar de eliminarlas
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE invites SET is_active = 0 
                WHERE user_id = ? AND guild_id = ?
            ''', (member.id, member.guild.id))
            
            conn.commit()
            conn.close()
            
            print(f"👋 {member.display_name} salió - invitación marcada como inactiva")
            
        except Exception as e:
            print(f"❌ Error procesando member_remove: {e}")
    
    def save_invitation(self, user_id: int, invited_by_id: int, guild_id: int, invite_code: str = None):
        """Guardar invitación en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO invites (user_id, invited_by_id, guild_id, invite_code, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, invited_by_id, guild_id, invite_code, datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            print(f"💾 Invitación guardada: {user_id} invitado por {invited_by_id}")
        except Exception as e:
            print(f"❌ Error guardando invitación: {e}")
    
    def get_user_invites_count(self, user_id: int, guild_id: int) -> int:
        """Obtener conteo de invitaciones activas de un usuario"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM invites 
                WHERE invited_by_id = ? AND guild_id = ? AND is_active = 1
            ''', (user_id, guild_id))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"❌ Error obteniendo conteo: {e}")
            return 0
    
    def get_user_inviter(self, user_id: int, guild_id: int) -> Optional[int]:
        """Obtener quién invitó a un usuario"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invited_by_id FROM invites 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (user_id, guild_id))
            
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"❌ Error obteniendo invitador: {e}")
            return None
    
    def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Tuple[int, int]]:
        """Obtener leaderboard de invitaciones"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invited_by_id, COUNT(*) as count
                FROM invites 
                WHERE guild_id = ? AND is_active = 1
                GROUP BY invited_by_id
                ORDER BY count DESC
                LIMIT ?
            ''', (guild_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"❌ Error obteniendo leaderboard: {e}")
            return []
    
    # ===== COMANDOS =====
    
    @commands.command(name="inv")
    async def inv_base(self, ctx):
        """🎫 Comando base del sistema de invitaciones"""
        embed = discord.Embed(
            title="🎫 Sistema de Invitaciones",
            description="¡El sistema está funcionando! Usa `help_invites` para ver todos los comandos.",
            color=0x00ff88
        )
        embed.add_field(
            name="📋 Comando de ayuda",
            value="`help_invites` - Ver todos los comandos",
            inline=False
        )
        embed.add_field(
            name="🧪 Comando de test",
            value="`test_invites` - Probar el sistema",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="debug_invites")
    @commands.has_permissions(manage_guild=True)
    async def debug_invites(self, ctx):
        """🔧 Debug del sistema de invitaciones (solo moderadores)"""
        try:
            # Obtener invitaciones actuales del servidor
            current_invites = await ctx.guild.invites()
            
            embed = discord.Embed(
                title="🔧 Debug del Sistema",
                color=0xffa500,
                timestamp=datetime.utcnow()
            )
            
            # Información del cache
            cached_invites = self.invite_cache.get(ctx.guild.id, {})
            embed.add_field(
                name="🧠 Cache",
                value=f"**{len(cached_invites)}** invitaciones en cache",
                inline=True
            )
            
            embed.add_field(
                name="📊 Servidor",
                value=f"**{len(current_invites)}** invitaciones activas",
                inline=True
            )
            
            # Mostrar algunas invitaciones
            if current_invites:
                invite_info = ""
                for i, invite in enumerate(current_invites[:5]):  # Mostrar máximo 5
                    cached_uses = "N/A"
                    if invite.code in cached_invites:
                        cached_uses = str(cached_invites[invite.code].uses)
                    
                    bot_indicator = " 🤖" if invite.inviter and invite.inviter.bot else ""
                    invite_info += f"`{invite.code}` - {invite.inviter.name if invite.inviter else 'Desconocido'}{bot_indicator}\n"
                    invite_info += f"  Usos actuales: {invite.uses} | Cache: {cached_uses}\n\n"
                
                embed.add_field(
                    name="🎫 Invitaciones (máximo 5)",
                    value=invite_info[:1000],  # Limitar caracteres
                    inline=False
                )
            
            # Verificar permisos
            perms = ctx.guild.me.guild_permissions
            embed.add_field(
                name="🔑 Permisos",
                value=f"Manage Server: {'✅' if perms.manage_guild else '❌'}\nCreate Invites: {'✅' if perms.create_instant_invite else '❌'}",
                inline=True
            )
            
            # Estado de la base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM invites WHERE guild_id = ?', (ctx.guild.id,))
            db_count = cursor.fetchone()[0]
            conn.close()
            
            embed.add_field(
                name="💾 Base de datos",
                value=f"**{db_count}** registros",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error en debug: {e}")
    
    @commands.command(name="refresh_invites", aliases=["reload_invites"])
    @commands.has_permissions(manage_guild=True)
    async def refresh_invites(self, ctx):
        """🔄 Refrescar cache de invitaciones manualmente"""
        try:
            invites = await ctx.guild.invites()
            self.invite_cache[ctx.guild.id] = {invite.code: invite for invite in invites}
            
            embed = discord.Embed(
                title="🔄 Cache Refrescado",
                description=f"Cache actualizado con **{len(invites)}** invitaciones",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
            print(f"🔄 Cache refrescado manualmente para {ctx.guild.name}")
            
        except Exception as e:
            await ctx.send(f"❌ Error refrescando cache: {e}")
    
    @commands.command(name="manual_invite")
    @commands.has_permissions(manage_guild=True)
    async def manual_invite(self, ctx, member: discord.Member, inviter: discord.Member):
        """➕ Registrar invitación manualmente (para testing)"""
        try:
            # Guardar en base de datos
            self.save_invitation(member.id, inviter.id, ctx.guild.id, "MANUAL")
            
            embed = discord.Embed(
                title="➕ Invitación Registrada Manualmente",
                description=f"**{member.mention}** ahora aparece como invitado por **{inviter.mention}**",
                color=0x00ff00
            )
            
            # Mostrar conteo actualizado
            count = self.get_user_invites_count(inviter.id, ctx.guild.id)
            embed.add_field(
                name="📊 Total de invitaciones",
                value=f"**{inviter.display_name}** ahora tiene **{count}** invitaciones",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name="test_invites", aliases=["invites_test", "test_inv"])
    async def test_invites(self, ctx):
        """🧪 Comando de prueba del sistema de invitaciones"""
        embed = discord.Embed(
            title="🧪 Test del Sistema de Invitaciones",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        try:
            # Verificar conexión a base de datos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM invites WHERE guild_id = ?', (ctx.guild.id,))
            total_invites = cursor.fetchone()[0]
            conn.close()
            
            embed.add_field(
                name="✅ Base de datos",
                value="Conectada correctamente",
                inline=True
            )
            
            embed.add_field(
                name="📊 Invitaciones registradas",
                value=f"{total_invites}",
                inline=True
            )
            
            # Verificar cache
            cache_count = len(self.invite_cache.get(ctx.guild.id, {}))
            embed.add_field(
                name="🧠 Cache de invitaciones",
                value=f"{cache_count} invitaciones",
                inline=True
            )
            
            # Verificar permisos
            permissions = ctx.guild.me.guild_permissions
            perms_status = "✅" if permissions.manage_guild else "❌"
            embed.add_field(
                name=f"{perms_status} Permisos",
                value="Manage Server" + (" ✓" if permissions.manage_guild else " ✗"),
                inline=True
            )
            
            embed.add_field(
                name="🤖 Estado del bot",
                value="Funcionando correctamente",
                inline=True
            )
            
            embed.add_field(
                name="📋 Comandos disponibles",
                value="`help_invites` para ver todos los comandos",
                inline=True
            )
            
            embed.set_footer(
                text=f"Test ejecutado por {ctx.author}",
                icon_url=ctx.author.display_avatar.url
            )
            
        except Exception as e:
            embed.color = 0xff0000
            embed.add_field(
                name="❌ Error",
                value=f"```{str(e)[:100]}```",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="help_invites", aliases=["invites_help", "help_inv", "ayuda_invites"])
    async def help_invites(self, ctx):
        """📖 Mostrar todos los comandos disponibles del sistema de invitaciones"""
        embed = discord.Embed(
            title="📖 Sistema de Invitaciones - Comandos",
            description="Todos los comandos disponibles para el sistema de invitaciones",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        # Comandos básicos
        embed.add_field(
            name="👤 Comandos de Usuario",
            value=(
                "`user_invites [usuario]` - Ver invitaciones de un usuario\n"
                "`who_invited [usuario]` - Ver quién invitó a alguien\n"
                "`invites_leaderboard [límite]` - Top de invitadores\n"
                "`my_rank` - Tu posición en el ranking"
            ),
            inline=False
        )
        
        # Comandos de moderación
        if ctx.author.guild_permissions.manage_guild:
            embed.add_field(
                name="🛡️ Comandos de Moderación",
                value=(
                    "`invites_info` - Estadísticas del sistema\n"
                    "`debug_invites` - Debug del sistema\n"
                    "`refresh_invites` - Refrescar cache\n"
                    "`manual_invite [usuario] [invitador]` - Registrar manualmente"
                ),
                inline=False
            )
        
        # Comandos de prueba
        embed.add_field(
            name="🧪 Comandos de Prueba",
            value=(
                "`test_invites` - Test del sistema\n"
                "`help_invites` - Mostrar esta ayuda"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Aliases disponibles",
            value=(
                "`invites` = `user_invites`\n"
                "`whoinvited` = `who_invited`\n"
                "`invlb` = `invites_leaderboard` = `top_invites`\n"
                "`help_invites` = `ayuda_invites`\n"
                "`test_invites` = `invites_test`"
            ),
            inline=False
        )
        
        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="user_invites", aliases=["invites", "invitaciones"])
    async def user_invites(self, ctx, member: discord.Member = None):
        """👤 Ver cuántas invitaciones ha hecho un usuario"""
        target = member or ctx.author
        count = self.get_user_invites_count(target.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Estadísticas de Invitaciones",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Usuario",
            value=f"{target.mention}\n`{target.name}`",
            inline=True
        )
        
        embed.add_field(
            name="🎫 Invitaciones",
            value=f"**{count}** persona(s)",
            inline=True
        )
        
        # Añadir badge
        badge = ""
        if count >= 50:
            badge = "🏆 **Leyenda de Invitaciones**"
        elif count >= 25:
            badge = "💎 **Maestro Invitador**"
        elif count >= 10:
            badge = "⭐ **Invitador Estrella**"
        elif count >= 5:
            badge = "🔥 **Invitador Activo**"
        elif count >= 1:
            badge = "🌟 **Primer Invitación**"
        
        if badge:
            embed.add_field(name="🏅 Badge", value=badge, inline=False)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="who_invited", aliases=["whoinvited", "quien_invito"])
    async def who_invited(self, ctx, member: discord.Member = None):
        """🔍 Ver quién invitó a un usuario"""
        target = member or ctx.author
        inviter_id = self.get_user_inviter(target.id, ctx.guild.id)
        
        embed = discord.Embed(
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        
        if not inviter_id:
            embed.title = "❓ Sin información"
            embed.description = f"No se encontró quién invitó a **{target.display_name}**"
            embed.color = 0xe74c3c
        else:
            inviter = ctx.guild.get_member(inviter_id)
            if inviter:
                embed.title = "🔍 Invitador Encontrado"
                embed.add_field(
                    name="👤 Usuario",
                    value=f"{target.mention}\n`{target.name}`",
                    inline=True
                )
                embed.add_field(
                    name="🎫 Invitado por",
                    value=f"{inviter.mention}\n`{inviter.name}`",
                    inline=True
                )
                embed.set_thumbnail(url=inviter.display_avatar.url)
            else:
                embed.title = "👻 Usuario no encontrado"
                embed.description = f"**{target.display_name}** fue invitado por alguien que ya no está en el servidor"
                embed.color = 0xf39c12
        
        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="invites_leaderboard", aliases=["invlb", "top_invites", "leaderboard_invites"])
    async def invites_leaderboard(self, ctx, limit: int = 10):
        """🏆 Top de usuarios con más invitaciones"""
        if limit > 25:
            limit = 25
        elif limit < 1:
            limit = 10
        
        results = self.get_leaderboard(ctx.guild.id, limit)
        
        if not results:
            embed = discord.Embed(
                title="🏆 Leaderboard de Invitaciones",
                description="Aún no hay invitaciones registradas en este servidor.",
                color=0xe74c3c
            )
        else:
            embed = discord.Embed(
                title="🏆 Leaderboard de Invitaciones",
                description=f"Top {len(results)} invitadores del servidor",
                color=0xf1c40f,
                timestamp=datetime.utcnow()
            )
            
            description = ""
            medals = ["🥇", "🥈", "🥉"]
            
            for i, (user_id, count) in enumerate(results):
                user = ctx.guild.get_member(user_id)
                if i < 3:
                    medal = medals[i]
                else:
                    medal = f"**{i+1}.**"
                
                name = user.display_name if user else "Usuario desconocido"
                description += f"{medal} {name} - **{count}** invitación(es)\n"
            
            embed.add_field(
                name="📊 Rankings",
                value=description,
                inline=False
            )
            
            # Encontrar posición del usuario que ejecuta el comando
            user_position = None
            for i, (user_id, count) in enumerate(results):
                if user_id == ctx.author.id:
                    user_position = i + 1
                    break
            
            if user_position:
                embed.add_field(
                    name="📍 Tu posición",
                    value=f"Estás en el puesto **#{user_position}**",
                    inline=False
                )
        
        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="my_rank", aliases=["mi_rango", "myrank", "my_position"])
    async def my_rank(self, ctx):
        """📍 Ver tu posición en el ranking de invitaciones"""
        results = self.get_leaderboard(ctx.guild.id, 100)  # Obtener más resultados para encontrar posición
        
        user_position = None
        user_count = 0
        
        for i, (user_id, count) in enumerate(results):
            if user_id == ctx.author.id:
                user_position = i + 1
                user_count = count
                break
        
        embed = discord.Embed(
            title="📍 Tu Posición en el Ranking",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )
        
        if user_position:
            embed.add_field(
                name="🏆 Posición",
                value=f"**#{user_position}**",
                inline=True
            )
            embed.add_field(
                name="🎫 Invitaciones",
                value=f"**{user_count}**",
                inline=True
            )
            
            # Calcular progreso al siguiente nivel
            if user_position > 1:
                next_user_count = results[user_position - 2][1]  # Usuario arriba
                needed = next_user_count - user_count + 1
                embed.add_field(
                    name="📈 Para subir",
                    value=f"Necesitas **{needed}** más",
                    inline=True
                )
        else:
            embed.description = "Aún no tienes invitaciones registradas. ¡Invita a algunos amigos!"
            embed.color = 0xe74c3c
        
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(
            text=f"Solicitado por {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="invites_info", aliases=["info_invites", "stats_invites"])
    @commands.has_permissions(manage_guild=True)
    async def invites_info(self, ctx):
        """📈 Información detallada del sistema (solo moderadores)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Estadísticas generales
            cursor.execute('SELECT COUNT(*) FROM invites WHERE guild_id = ? AND is_active = 1', (ctx.guild.id,))
            active_invites = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM invites WHERE guild_id = ? AND is_active = 0', (ctx.guild.id,))
            inactive_invites = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT invited_by_id) FROM invites WHERE guild_id = ? AND is_active = 1', (ctx.guild.id,))
            unique_inviters = cursor.fetchone()[0]
            
            # Mejor invitador
            cursor.execute('''
                SELECT invited_by_id, COUNT(*) as count
                FROM invites 
                WHERE guild_id = ? AND is_active = 1
                GROUP BY invited_by_id
                ORDER BY count DESC
                LIMIT 1
            ''', (ctx.guild.id,))
            
            top_inviter_data = cursor.fetchone()
            conn.close()
            
            embed = discord.Embed(
                title="📈 Información del Sistema de Invitaciones",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📊 Estadísticas Generales",
                value=(
                    f"**Invitaciones activas:** {active_invites}\n"
                    f"**Invitaciones inactivas:** {inactive_invites}\n"
                    f"**Total:** {active_invites + inactive_invites}\n"
                    f"**Usuarios que han invitado:** {unique_inviters}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🧠 Cache del Sistema",
                value=f"**{len(self.invite_cache.get(ctx.guild.id, {}))}** invitaciones en cache",
                inline=True
            )
            
            # Información del mejor invitador
            if top_inviter_data:
                top_inviter = ctx.guild.get_member(top_inviter_data[0])
                top_inviter_name = top_inviter.display_name if top_inviter else "Usuario desconocido"
                embed.add_field(
                    name="👑 Mejor Invitador",
                    value=f"**{top_inviter_name}**\n{top_inviter_data[1]} invitaciones",
                    inline=True
                )
            
            embed.set_footer(text=f"Servidor: {ctx.guild.name}")
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error obteniendo información: {e}")
    
    # Comando de error handler para el cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Manejar errores específicos del cog de invitaciones"""
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tienes permisos para usar este comando.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Setup function para cargar el cog"""
    print("🔧 Ejecutando setup() del módulo invitaciones...")
    try:
        await bot.add_cog(Invites(bot))
        print("✅ Setup completado para módulo invitaciones")
    except Exception as e:
        print(f"❌ Error en setup: {e}")
        raise