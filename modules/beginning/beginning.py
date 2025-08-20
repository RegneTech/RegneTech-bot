import discord
from discord.ext import commands
import asyncio

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuración de canales
        self.VERIFICATION_CHANNEL_ID = 1400106792821981245
        self.RULES_CHANNEL_ID = 1400106792821981246
        self.FUNCIONAMIENTO_CHANNEL_ID = 1400106793551663187
        self.AUTOROLES_CHANNEL_ID = 1403015632844488839
        self.REWARDS_CHANNEL_ID = 1406413774147158086
        self.VERIFIED_ROLE_ID = 1400106792196898888
        self.AUTO_ROLE_ID = 1406360634643316746
        self.RESENADOR_ROLE_ID = 1400106792196898891
        self.BUMPEADOR_ROLE_ID = 1400106792196898892
        self.NUEVO_ROLE_ID = 1406641834553380884
        self.RANGO_PREFIX = "◈ Rango"
        
        # Control de operaciones en progreso para evitar conflictos
        self._role_operations = set()
        
        # Diccionario de roles por nivel
        self.LEVEL_ROLES = {
            200: 1400106792280658067,  190: 1400106792280658066,
            180: 1400106792280658065,  170: 1400106792280658064,
            160: 1400106792280658063,  150: 1400106792280658062,
            140: 1400106792280658061,  130: 1400106792226127923,
            120: 1400106792226127922,  110: 1400106792226127921,
            100: 1400106792226127920,  90: 1400106792226127919,
            80: 1400106792226127918,   70: 1400106792226127917,
            60: 1400106792226127916,   50: 1400106792226127915,
            40: 1400106792226127914,   30: 1400106792196898895,
            20: 1400106792196898894,   10: 1400106792196898893,
        }
        
        # Recompensas por nivel
        self.LEVEL_REWARDS = {
            200: ["Beneficio acumulado de todos los anteriores + diseño de perfil único que nadie más puede tener."],
            190: ["Acceso a \"misiones legendarias\" con premios exclusivos."],
            180: ["Multiplicador de recompensas en torneos y eventos (+50%)."],
            170: ["Acceso a encuestas exclusivas de decisiones del servidor."],
            160: ["Acceso a canal de leaks/spoilers VIP."],
            150: ["x4 de XP durante 78h + logro exclusivo."],
            140: ["x2 de suerte en eventos y similares."],
            130: ["Perfil único personalizado que usarás tú y estará en la tienda."],
            120: ["Ganar más de 1€ por reseña."],
            110: ["Rol exclusivo y acceso a misiones."],
            100: ["Comprar diseños de perfil en la tienda."],
            90: ["Acceso a sorteos gratis y torneos."],
            80: ["x3 de XP durante 78h + logro exclusivo."],
            70: ["Acceso a canal privado + añadir emojis."],
            60: ["Diseño de perfil exclusivo + gama de colores."],
            50: ["x2 de XP durante 78h + logro exclusivo."],
            40: ["Permisos para gifs e imágenes dentro del servidor."],
            30: ["Desbloquea gama de colores para personalizar perfil."],
            20: ["Sube precio inicial de 0.3 a 0.5 en reseñas."],
            10: ["Cambiar color del nombre y cambiar apodo."]
        }

    # ╔══ FUNCIONES AUXILIARES MEJORADAS ══╗
    
    def has_rango_role(self, member):
        """Verifica si el miembro tiene algún rol de rango"""
        return any(role.name.startswith(self.RANGO_PREFIX) for role in member.roles)
    
    async def safe_role_operation(self, member, operation_type, *roles):
        """Realiza operaciones de roles de forma segura evitando conflictos"""
        user_key = f"{member.id}_{operation_type}"
        
        # Evitar operaciones concurrentes en el mismo usuario
        if user_key in self._role_operations:
            print(f"⚠️ Operación {operation_type} ya en progreso para {member.display_name}")
            return False
        
        self._role_operations.add(user_key)
        
        try:
            if operation_type == "add":
                await member.add_roles(*roles, reason="Gestión automática de roles")
                print(f"✅ Roles añadidos a {member.display_name}: {[r.name for r in roles]}")
            elif operation_type == "remove":
                await member.remove_roles(*roles, reason="Gestión automática de roles")
                print(f"✅ Roles removidos de {member.display_name}: {[r.name for r in roles]}")
            return True
            
        except discord.Forbidden:
            print(f"❌ Sin permisos para gestionar roles de {member.display_name}")
            return False
        except discord.HTTPException as e:
            print(f"❌ Error HTTP gestionando roles de {member.display_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado gestionando roles de {member.display_name}: {e}")
            return False
        finally:
            # Remover de operaciones en progreso después de un delay
            await asyncio.sleep(1)
            self._role_operations.discard(user_key)

    async def manage_auto_role(self, member):
        """Gestiona el rol automático basado en si tiene rol de rango"""
        try:
            verified_role = member.guild.get_role(self.VERIFIED_ROLE_ID)
            auto_role = member.guild.get_role(self.AUTO_ROLE_ID)
            
            if not verified_role or not auto_role:
                print("❌ No se encontraron los roles necesarios")
                return
            
            # Solo proceder si el usuario está verificado
            if verified_role not in member.roles:
                return
            
            has_rango = self.has_rango_role(member)
            has_auto = auto_role in member.roles
            
            print(f"🔍 Analizando {member.display_name}: Rango={has_rango}, Auto={has_auto}")
            
            if has_rango and has_auto:
                # Tiene rol de rango pero también el automático -> remover automático
                await self.safe_role_operation(member, "remove", auto_role)
                
            elif not has_rango and not has_auto:
                # No tiene rol de rango ni automático -> añadir automático
                await self.safe_role_operation(member, "add", auto_role)
                
        except Exception as e:
            print(f"❌ Error en manage_auto_role para {member.display_name}: {e}")

    # ╔══ EVENTOS DE DISCORD MEJORADOS ══╗
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Evento mejorado que gestiona cambios de roles"""
        # Solo proceder si hay cambios en los roles
        if before.roles == after.roles:
            return
        
        # Pequeño delay para evitar spam de eventos
        await asyncio.sleep(0.5)
        
        try:
            # Obtener roles añadidos y removidos
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            # Verificar cambios en roles de rango
            rango_added = any(role.name.startswith(self.RANGO_PREFIX) for role in added_roles)
            rango_removed = any(role.name.startswith(self.RANGO_PREFIX) for role in removed_roles)
            
            # Solo gestionar si hubo cambios relevantes
            if rango_added or rango_removed:
                print(f"🔄 Detectado cambio de rol de rango en {after.display_name}")
                await self.manage_auto_role(after)
                
        except Exception as e:
            print(f"❌ Error en on_member_update: {e}")

    async def cog_load(self):
        """Configuración automática al cargar el cog"""
        print("🔧 Configurando sistemas automáticamente...")
        
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)  # Delay adicional para estabilidad
        
        try:
            await self.setup_verification()
            print("✅ Sistema de verificación configurado automáticamente")
        except Exception as e:
            print(f"❌ Error configurando verificación: {str(e)}")
        
        try:
            for guild in self.bot.guilds:
                await self.setup_autoroles(guild)
                print(f"✅ Autoroles configurados en {guild.name}")
                break
        except Exception as e:
            print(f"❌ Error configurando autoroles: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Backup para configuración automática"""
        if not hasattr(self, '_auto_setup_done'):
            self._auto_setup_done = True
            await asyncio.sleep(3)
            
            try:
                await self.setup_verification()
                print("✅ Verificación configurada (on_ready)")
            except Exception as e:
                print(f"❌ Error en setup automático: {e}")

    # ╔══ COMANDOS DE ADMINISTRACIÓN ══╗
    
    @commands.command(name="fix_roles")
    @commands.has_permissions(administrator=True)
    async def fix_roles(self, ctx):
        """Corrige los roles automáticos de todos los usuarios verificados"""
        loading_msg = await ctx.send("🔄 Analizando y corrigiendo roles...")
        
        verified_role = ctx.guild.get_role(self.VERIFIED_ROLE_ID)
        if not verified_role:
            await loading_msg.edit(content="❌ Rol de verificado no encontrado")
            return
        
        fixed_count = 0
        verified_members = [m for m in ctx.guild.members if verified_role in m.roles]
        
        for member in verified_members:
            try:
                old_has_rango = self.has_rango_role(member)
                await self.manage_auto_role(member)
                fixed_count += 1
                
                # Pequeño delay para evitar rate limits
                if fixed_count % 10 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error corrigiendo {member.display_name}: {e}")
        
        embed = discord.Embed(
            title="🛠️ Corrección de Roles Completada",
            description=f"Se analizaron **{len(verified_members)}** usuarios verificados.\n"
                       f"Operaciones realizadas en **{fixed_count}** usuarios.",
            color=0x00ff00
        )
        
        await loading_msg.edit(content="", embed=embed)

    @commands.command(name="roles_status")
    @commands.has_permissions(administrator=True)
    async def roles_status(self, ctx):
        """Muestra estadísticas detalladas del sistema de roles"""
        verified_role = ctx.guild.get_role(self.VERIFIED_ROLE_ID)
        auto_role = ctx.guild.get_role(self.AUTO_ROLE_ID)
        
        if not verified_role or not auto_role:
            await ctx.send("❌ No se encontraron los roles necesarios")
            return
        
        # Estadísticas
        verified_members = [m for m in ctx.guild.members if verified_role in m.roles]
        auto_members = [m for m in verified_members if auto_role in m.roles]
        rango_members = [m for m in verified_members if self.has_rango_role(m)]
        
        embed = discord.Embed(
            title="🎭 Estado del Sistema de Roles",
            color=0x00ffff
        )
        
        embed.add_field(
            name="📊 Estadísticas Generales",
            value=f"**Total verificados:** {len(verified_members)}\n"
                  f"**Con rol automático:** {len(auto_members)}\n"
                  f"**Con rol de rango:** {len(rango_members)}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Configuración",
            value=f"**Verificado:** {verified_role.mention}\n"
                  f"**Automático:** {auto_role.mention}\n"
                  f"**Prefijo Rango:** `{self.RANGO_PREFIX}`",
            inline=True
        )
        
        # Verificar posibles inconsistencias
        inconsistencies = []
        for member in verified_members:
            has_rango = self.has_rango_role(member)
            has_auto = auto_role in member.roles
            
            if has_rango and has_auto:
                inconsistencies.append(f"• {member.display_name} (tiene ambos)")
            elif not has_rango and not has_auto:
                inconsistencies.append(f"• {member.display_name} (no tiene ninguno)")
        
        if inconsistencies:
            embed.add_field(
                name="⚠️ Inconsistencias Detectadas",
                value="\n".join(inconsistencies[:5]) + 
                      (f"\n... y {len(inconsistencies)-5} más" if len(inconsistencies) > 5 else ""),
                inline=False
            )
            embed.add_field(
                name="🛠️ Solución",
                value="Usa `!fix_roles` para corregir automáticamente",
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Estado",
                value="No se detectaron inconsistencias",
                inline=False
            )
        
        await ctx.send(embed=embed)

    # ╔══ RESTO DE FUNCIONES (MANTENIDAS) ══╗
    
    async def clear_channel(self, channel):
        """Limpia todos los mensajes del canal"""
        try:
            deleted = await channel.purge()
            return len(deleted)
        except discord.Forbidden:
            return 0
        except Exception:
            return 0

    async def setup_verification(self):
        """Configura el sistema de verificación"""
        channel = self.bot.get_channel(self.VERIFICATION_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de verificación no encontrado")
        
        await self.clear_channel(channel)
        
        embed = discord.Embed(
            title="Verificación del Servidor",
            description="¡Bienvenido a nuestro servidor!\n\n"
                       "Para acceder a todos los canales y participar en la comunidad, "
                       "necesitas verificarte primero.\n\n"
                       "**Haz clic en el botón de abajo para completar tu verificación** ⬇️",
            color=0x2b2d31
        )
        
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        
        embed.add_field(
            name="¿Por qué verificarse?", 
            value="• Acceso completo al servidor\n• Participar en conversaciones\n• Unirte a eventos y actividades", 
            inline=False
        )
        
        embed.set_footer(
            text=f"Servidor: {channel.guild.name} | Miembros: {channel.guild.member_count}",
            icon_url=channel.guild.icon.url if channel.guild.icon else None
        )
        
        view = VerificationView(self.VERIFIED_ROLE_ID, self.AUTO_ROLE_ID, self.RULES_CHANNEL_ID, self.RANGO_PREFIX, self)
        await channel.send(embed=embed, view=view)

    async def setup_autoroles(self, guild):
        """Configura el sistema de autoroles"""
        channel = self.bot.get_channel(self.AUTOROLES_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de autoroles no encontrado")
        
        await self.clear_channel(channel)
        
        embed = discord.Embed(
            title="Sistema de Autoroles",
            description="¡Personaliza tu experiencia en el servidor! Selecciona los roles que más te interesen para recibir notificaciones específicas y acceder a funciones exclusivas.\n\n"
                       "**Haz clic en los botones de abajo para obtener o quitar tus roles:**",
            color=0x7F8C8D
        )
        
        embed.add_field(
            name="【📚 RESEÑADOR】",
            value="Recibe notificaciones cada vez que haya nuevas reseñas disponibles para completar y ganar dinero real.",
            inline=False
        )
        
        embed.add_field(
            name="【🚀 BUMPEADOR】", 
            value="Ayuda a hacer crecer el servidor y recibe notificaciones cuando sea momento de hacer bump en el servidor.",
            inline=False
        )
        
        embed.add_field(
            name="【✨ PARTNER PING】", 
            value="Recibe notificaciones cada vez que haya un nuevo partner para poder ver lo que ofrecen en otros servidores.",
            inline=False
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(
            text=f"Autoroles de {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        view = AutoRolesView(self.RESENADOR_ROLE_ID, self.BUMPEADOR_ROLE_ID, self.NUEVO_ROLE_ID)
        await channel.send(embed=embed, view=view)

    # Comandos adicionales (mantenidos igual)
    @commands.command(name="verify_setup")
    @commands.has_permissions(administrator=True)
    async def verify_setup(self, ctx):
        try:
            await self.setup_verification()
            await ctx.send(f"✅ Sistema de verificación configurado en <#{self.VERIFICATION_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name="autoroles_setup")
    @commands.has_permissions(administrator=True)
    async def autoroles_setup(self, ctx):
        try:
            await self.setup_autoroles(ctx.guild)
            await ctx.send(f"✅ Autoroles configurados en <#{self.AUTOROLES_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

class AutoRolesView(discord.ui.View):
    def __init__(self, resenador_role_id, bumpeador_role_id, nuevo_role_id):
        super().__init__(timeout=None)
        self.resenador_role_id = resenador_role_id
        self.bumpeador_role_id = bumpeador_role_id
        self.nuevo_role_id = nuevo_role_id

    @discord.ui.button(label="【📚】", style=discord.ButtonStyle.gray, custom_id="resenador_role")
    async def resenador_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_role_toggle(interaction, self.resenador_role_id, "Reseñador")

    @discord.ui.button(label="【🚀】", style=discord.ButtonStyle.gray, custom_id="bumpeador_role")
    async def bumpeador_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_role_toggle(interaction, self.bumpeador_role_id, "Bumpeador")

    @discord.ui.button(label="【✨】", style=discord.ButtonStyle.gray, custom_id="nuevo_role")
    async def nuevo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_role_toggle(interaction, self.nuevo_role_id, "Partner Ping")

    async def _handle_role_toggle(self, interaction: discord.Interaction, role_id: int, role_name: str):
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message(
                f"❌ Error: No se pudo encontrar el rol de {role_name}.", 
                ephemeral=True
            )
            return
        
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    f"❌ Te has quitado el rol **{role.name}**.",
                    ephemeral=True
                )
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    f"✅ ¡Te has asignado el rol **{role.name}**!",
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Error: No tengo permisos para gestionar este rol.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}", 
                ephemeral=True
            )

class VerificationView(discord.ui.View):
    def __init__(self, verified_role_id, auto_role_id, rules_channel_id, rango_prefix, cog):
        super().__init__(timeout=None)
        self.verified_role_id = verified_role_id
        self.auto_role_id = auto_role_id
        self.rules_channel_id = rules_channel_id
        self.rango_prefix = rango_prefix
        self.cog = cog

    @discord.ui.button(label="🔐 Verificarme", style=discord.ButtonStyle.green, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        verified_role = interaction.guild.get_role(self.verified_role_id)
        auto_role = interaction.guild.get_role(self.auto_role_id)
        
        if not verified_role or not auto_role:
            await interaction.response.send_message(
                "❌ Error: No se pudieron encontrar los roles necesarios.", 
                ephemeral=True
            )
            return
        
        if verified_role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ Ya estás verificado.", 
                ephemeral=True
            )
            return
        
        try:
            # Verificar si tiene rol de rango
            has_rango = self.cog.has_rango_role(interaction.user)
            
            # Preparar roles a asignar
            roles_to_add = [verified_role]
            if not has_rango:
                roles_to_add.append(auto_role)
            
            # Asignar roles usando el método seguro del cog
            success = await self.cog.safe_role_operation(interaction.user, "add", *roles_to_add)
            
            if not success:
                await interaction.response.send_message(
                    "❌ Error: No se pudieron asignar los roles. Contacta con un administrador.", 
                    ephemeral=True
                )
                return
            
            # Crear mensaje de bienvenida
            rules_channel = interaction.guild.get_channel(self.rules_channel_id)
            
            welcome_embed = discord.Embed(
                title="🎉 ¡Verificación completada!",
                description=f"¡Bienvenido oficial a **{interaction.guild.name}**!\n\n"
                           f"✅ Has sido verificado correctamente y ahora tienes acceso completo al servidor.",
                color=0x00ff00
            )
            
            roles_info = f"**Roles asignados:**\n• {verified_role.name}"
            if auto_role in roles_to_add:
                roles_info += f"\n• {auto_role.name}"
                roles_info += f"\n\n*El rol automático se gestiona según tus roles de rango*"
            else:
                roles_info += f"\n\n*No se asignó el rol automático porque tienes un rol de rango*"
            
            welcome_embed.add_field(
                name="🎭 Información de Roles",
                value=roles_info,
                inline=False
            )
            
            if rules_channel:
                welcome_embed.add_field(
                    name="📋 Próximos pasos",
                    value=f"• Lee nuestras reglas en {rules_channel.mention}\n"
                          f"• Explora los diferentes canales\n"
                          f"• ¡Preséntate con la comunidad!",
                    inline=False
                )
            
            if interaction.guild.icon:
                welcome_embed.set_thumbnail(url=interaction.guild.icon.url)
            
            welcome_embed.set_footer(
                text=f"¡Disfruta tu estancia en {interaction.guild.name}!",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.response.send_message(
                embed=welcome_embed,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error inesperado durante la verificación: {str(e)}", 
                ephemeral=True
            )
            print(f"❌ Error en verificación de {interaction.user.display_name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))