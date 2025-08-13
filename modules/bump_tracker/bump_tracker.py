import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone
from database import add_bump, get_bumps, get_all_bumps

# Configuración del Bump Tracker
DISBOARD_BOT_ID = 302050872383242240
ROLE_ID_TO_PING = 1400106792196898892
CHANNEL_ID = 1400106793249538050
COUNTDOWN = 2 * 60 * 60  # 2 horas
EMBED_COLOR = 0x00ffff


class BumpTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tasks: dict[int, asyncio.Task] = {}
        self.pending_bumps: dict[int, int] = {}  # guild_id → user_id que ejecutó el bump

    # ────────────────────────────────────────
    # Comando de ayuda para bumps
    # ────────────────────────────────────────
    @commands.command(name="help_bumps")
    async def help_bumps(self, ctx: commands.Context):
        """Muestra todos los comandos disponibles del sistema de bumps"""
        
        embed = discord.Embed(
            title="🚀 Sistema de Bump Tracker - Comandos Disponibles",
            description="Lista completa de comandos para el sistema de bumps del servidor:",
            color=EMBED_COLOR
        )
        
        # Comandos para usuarios
        embed.add_field(
            name="👥 Comandos para Usuarios",
            value="• `!bumpstats` - Ver tus estadísticas personales de bumps\n"
                  "• `!clasificacion` - Ver el ranking completo de bumps\n"
                  "• `!bumprank` - Alias para el comando clasificacion\n"
                  "• `!help_bumps` - Mostrar esta ayuda",
            inline=False
        )
        
        # Comandos para administradores
        embed.add_field(
            name="🛠️ Comandos para Administradores",
            value="• `!testbump` / `!tbump` / `!btest` - Simular un bump para pruebas\n"
                  "  *(Solo funciona en el canal de bumps)*\n"
                  "• `!debugbump` - Activar/desactivar logs de debugging",
            inline=False
        )
        
        # Información del sistema
        embed.add_field(
            name="ℹ️ Información del Sistema",
            value=f"• **Canal de bumps:** <#{CHANNEL_ID}>\n"
                  f"• **Rol notificado:** <@&{ROLE_ID_TO_PING}>\n"
                  f"• **Tiempo de recordatorio:** 2 horas\n"
                  f"• **Bot detectado:** <@{DISBOARD_BOT_ID}>",
            inline=False
        )
        
        # Funcionamiento automático
        embed.add_field(
            name="🤖 Funcionamiento Automático",
            value="• El sistema detecta automáticamente cuando usas `/bump`\n"
                  "• Registra tus bumps en la base de datos\n"
                  "• Envía un agradecimiento tras cada bump exitoso\n"
                  "• Programa recordatorios automáticos cada 2 horas\n"
                  "• Elimina mensajes de comandos fallidos de Disboard",
            inline=False
        )
        
        # Notas importantes
        embed.add_field(
            name="📌 Notas Importantes",
            value="• Los bumps solo se registran si son exitosos\n"
                  "• El sistema funciona únicamente en el canal configurado\n"
                  "• Los recordatorios mencionan al rol configurado\n"
                  "• Los tests de administrador usan un countdown de 30 segundos",
            inline=False
        )
        
        # Agregar imagen del servidor si está disponible
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        embed.set_footer(
            text=f"Sistema de bumps de {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await ctx.send(embed=embed)

    # ───────────── listener para TODOS los mensajes del canal ─────────────
    @commands.Cog.listener("on_message")
    async def monitor_all_messages(self, message: discord.Message):
        # Solo procesar mensajes del canal configurado
        if message.channel.id != CHANNEL_ID:
            return

        print(f"[BUMP DEBUG] Mensaje detectado en canal bumps:")
        print(f"  - Autor: {message.author} (ID: {message.author.id})")
        print(f"  - Contenido: '{message.content}'")
        print(f"  - Es bot: {message.author.bot}")
        print(f"  - Tiene interaction: {message.interaction is not None}")

        # Procesar mensajes de Disboard
        if message.author.id == DISBOARD_BOT_ID:
            print(f"[BUMP DEBUG] Mensaje de DISBOARD detectado")
            await self.disboard_only_bump(message)
            return

        # Detectar comandos /bump de usuarios (texto plano o slash command)
        content_lower = message.content.strip().lower()
        if content_lower == "/bump" or content_lower.startswith("/bump "):
            print(f"[BUMP DEBUG] Comando /bump detectado de usuario {message.author.id}")
            self.pending_bumps[message.guild.id] = message.author.id
            print(f"[BUMP DEBUG] Usuario {message.author.id} agregado a pending_bumps")

    # ───────────── procesamiento de mensajes de DISBOARD ─────────────
    async def disboard_only_bump(self, message: discord.Message):
        print(f"[BUMP DEBUG] Procesando mensaje de Disboard...")
        print(f"  - Interaction: {message.interaction}")
        print(f"  - Content: '{message.content}'")
        print(f"  - Embeds count: {len(message.embeds)}")
        
        # Manejar slash commands de Disboard
        if message.interaction:
            cmd = (message.interaction.name or "").lower()
            user_id = message.interaction.user.id
            
            print(f"[BUMP DEBUG] Slash command detectado:")
            print(f"  - Comando: '{cmd}'")
            print(f"  - Usuario: {user_id}")

            if cmd == "bump":
                self.pending_bumps[message.guild.id] = user_id
                print(f"[BUMP DEBUG] Usuario {user_id} registrado en pending_bumps para slash command")
            else:
                print(f"[BUMP DEBUG] Comando '{cmd}' no es bump, eliminando mensaje")
                try:
                    await message.delete()
                except discord.Forbidden:
                    print(f"[BUMP DEBUG] Sin permisos para eliminar mensaje")
                except Exception as e:
                    print(f"[BUMP DEBUG] Error eliminando mensaje: {e}")
                return

        # Verificar si el mensaje tiene embeds
        if not message.embeds:
            print(f"[BUMP DEBUG] Mensaje sin embeds")
            # Si no hay embeds pero hay contenido de texto, verificar si es un error
            if message.content:
                print(f"[BUMP DEBUG] Contenido de texto: '{message.content}'")
                # Si es un mensaje de error, eliminarlo
                if any(error_word in message.content.lower() for error_word in 
                       ["error", "cooldown", "wait", "espera", "comando no válido"]):
                    try:
                        await message.delete()
                        print(f"[BUMP DEBUG] Mensaje de error eliminado")
                    except:
                        pass
            return

        # Analizar el embed principal
        embed = message.embeds[0]
        title = embed.title or ""
        description = embed.description or ""
        
        print(f"[BUMP DEBUG] Analizando embed:")
        print(f"  - Title: '{title}'")
        print(f"  - Description: '{description[:200]}...' (truncado)")
        
        # Texto combinado para análisis
        combined_text = f"{title} {description}".lower()
        print(f"[BUMP DEBUG] Texto combinado (primeros 200 chars): '{combined_text[:200]}...'")

        # Patrones de éxito expandidos (incluye múltiples idiomas y variaciones)
        success_patterns = [
            # Inglés
            "bump done", "bumped", "bump successful", "bump complete",
            "server bumped", "successfully bumped", "bump executed",
            
            # Español
            "¡hecho!", "bumpeado", "bump realizado", "servidor bumpeado",
            "bump exitoso", "bump completado", "¡realizado!",
            
            # Otros posibles patrones
            "✅", "done!", "success", "complete", "finished"
        ]
        
        # Verificar si es un bump exitoso
        is_success = any(pattern in combined_text for pattern in success_patterns)
        print(f"[BUMP DEBUG] ¿Es bump exitoso? {is_success}")
        
        # También verificar por color del embed (Disboard suele usar verde para éxito)
        embed_color = embed.color
        if embed_color:
            print(f"[BUMP DEBUG] Color del embed: {embed_color}")
            # Verde típico de éxito
            if embed_color.value in [0x00ff00, 0x00d166, 0x57f287, 0x5865f2]:
                is_success = True
                print(f"[BUMP DEBUG] Bump exitoso detectado por color verde")

        if not is_success:
            print(f"[BUMP DEBUG] No es bump exitoso, verificando si es error para eliminar")
            
            # Verificar si es un mensaje de error o cooldown
            error_patterns = [
                "cooldown", "wait", "espera", "error", "failed", "falló",
                "try again", "intenta de nuevo", "not ready", "no está listo",
                "please wait", "por favor espera"
            ]
            
            is_error = any(pattern in combined_text for pattern in error_patterns)
            print(f"[BUMP DEBUG] ¿Es mensaje de error? {is_error}")
            
            if is_error:
                try:
                    await message.delete()
                    print(f"[BUMP DEBUG] Mensaje de error eliminado")
                except discord.Forbidden:
                    print(f"[BUMP DEBUG] Sin permisos para eliminar mensaje de error")
                except Exception as e:
                    print(f"[BUMP DEBUG] Error eliminando mensaje: {e}")
            
            return

        # Procesar bump exitoso
        guild_id = message.guild.id
        print(f"[BUMP DEBUG] Procesando bump exitoso para guild {guild_id}")
        print(f"[BUMP DEBUG] Pending bumps actuales: {self.pending_bumps}")
        
        if guild_id not in self.pending_bumps:
            print(f"[BUMP DEBUG] ⚠️ No hay usuario pendiente para guild {guild_id}")
            print(f"[BUMP DEBUG] Esto puede indicar que el comando fue ejecutado hace tiempo")
            # En caso de que no tengamos el usuario, intentar obtenerlo del interaction
            if message.interaction and message.interaction.user:
                user_id = message.interaction.user.id
                print(f"[BUMP DEBUG] Usando usuario del interaction: {user_id}")
            else:
                print(f"[BUMP DEBUG] No se puede determinar el usuario, abortando")
                return
        else:
            user_id = self.pending_bumps.pop(guild_id)
            print(f"[BUMP DEBUG] Usuario obtenido de pending_bumps: {user_id}")

        # Registrar bump en base de datos
        try:
            total = await add_bump(user_id, guild_id)
            print(f"[BUMP DEBUG] Bump registrado en BD. Total del usuario: {total}")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error registrando bump en BD: {e}")
            return

        # Enviar mensaje de agradecimiento
        try:
            thanks = discord.Embed(
                description=(
                    "🙌 **¡Mil gracias!**\n"
                    f"💖 Agradecemos que hayas bumpeado nuestro servidor, <@{user_id}>.\n"
                    f"🌟 Has realizado **{total}** bumps en total. ¡Fantástico!"
                ),
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            await message.channel.send(embed=thanks)
            print(f"[BUMP DEBUG] ✅ Mensaje de agradecimiento enviado")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error enviando mensaje de agradecimiento: {e}")

        # Programar recordatorio
        try:
            # Cancelar tarea previa si existe
            if task := self.tasks.get(guild_id):
                task.cancel()
                print(f"[BUMP DEBUG] Tarea anterior cancelada")
            
            # Crear nueva tarea de recordatorio
            self.tasks[guild_id] = self.bot.loop.create_task(self._recordatorio(message.channel))
            print(f"[BUMP DEBUG] ✅ Recordatorio programado para 2 horas")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error programando recordatorio: {e}")

    async def _recordatorio(self, channel: discord.TextChannel):
        try:
            print(f"[BUMP DEBUG] Recordatorio iniciado, esperando {COUNTDOWN} segundos...")
            await asyncio.sleep(COUNTDOWN)
            print(f"[BUMP DEBUG] Tiempo de espera completado, enviando recordatorio")
        except asyncio.CancelledError:
            print(f"[BUMP DEBUG] Recordatorio cancelado")
            return

        try:
            role = channel.guild.get_role(ROLE_ID_TO_PING)
            mention = role.mention if role else "@here"

            embed = discord.Embed(
                description=(
                    "🕐 **¡Es momento de hacer un bump!**\n"
                    "Utiliza **/bump** para apoyar al servidor.\n\n"
                    "*Sistema de recordatorio de bump*"
                ),
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            await channel.send(content=mention, embed=embed)
            print(f"[BUMP DEBUG] ✅ Recordatorio enviado exitosamente")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error enviando recordatorio: {e}")

    # ────────────────────────────────────────
    # Función auxiliar para obtener ranking
    # ────────────────────────────────────────
    async def get_bump_ranking(self, guild_id: int):
        """Obtiene el ranking de bumps ordenado descendentemente"""
        try:
            bumps = await get_all_bumps(guild_id)
            return bumps  # Ya viene ordenado de get_all_bumps
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error obteniendo ranking: {e}")
            return []

    # ────────────────────────────────────────
    # Comando: ver estadísticas personales de bumps
    # ────────────────────────────────────────
    @commands.command(name="bumpstats")
    async def bump_stats(self, ctx: commands.Context):
        """Muestra las estadísticas personales de bumps del usuario con su posición en el ranking"""
        try:
            # Obtener bumps del usuario
            user_bumps = await get_bumps(ctx.author.id, ctx.guild.id)
            
            # Obtener ranking para calcular posición
            ranking = await self.get_bump_ranking(ctx.guild.id)
            
            # Encontrar posición del usuario
            user_position = None
            total_users = len(ranking)
            
            for i, (user_id, bumps) in enumerate(ranking, 1):
                if user_id == ctx.author.id:
                    user_position = i
                    break
            
            # Si no está en el ranking, está en última posición
            if user_position is None:
                user_position = total_users + 1 if user_bumps == 0 else total_users
            
            embed = discord.Embed(
                title="📊 Tus estadísticas de Bump",
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="🚀 Bumps realizados",
                value=f"**{user_bumps}** bumps",
                inline=True
            )
            
            embed.add_field(
                name="🏆 Posición en ranking",
                value=f"**#{user_position}** de {total_users}",
                inline=True
            )
            
            # Calcular porcentaje si tiene bumps
            if user_bumps > 0 and ranking:
                total_bumps = sum(bumps for _, bumps in ranking)
                percentage = (user_bumps / total_bumps) * 100 if total_bumps > 0 else 0
                
                embed.add_field(
                    name="📈 Contribución",
                    value=f"**{percentage:.1f}%** del total",
                    inline=True
                )
            
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            
            # Mensaje motivacional basado en posición
            if user_position == 1:
                footer_msg = "🥇 ¡Eres el #1 en bumps!"
            elif user_position <= 3:
                footer_msg = f"🥈 ¡Estás en el top 3!"
            elif user_position <= 10:
                footer_msg = f"🔥 ¡Estás en el top 10!"
            else:
                footer_msg = "💪 ¡Sigue bumpeando para subir de posición!"
            
            embed.set_footer(text=footer_msg)
            
            await ctx.send(embed=embed)
            print(f"[BUMP DEBUG] Estadísticas mostradas para usuario {ctx.author.id} - Posición: {user_position}")
            
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error en bumpstats: {e}")
            await ctx.send("❌ Error obteniendo estadísticas. Intenta de nuevo.")

    # ────────────────────────────────────────
    # Comando: ranking completo de bumps
    # ────────────────────────────────────────
    @commands.command(name="clasificacion")
    async def clasificacion(self, ctx):
        """Muestra el ranking de usuarios por cantidad de bumps"""
        try:
            bumps = await get_all_bumps(ctx.guild.id)
            if not bumps:
                embed = discord.Embed(
                    title="❌ Sin datos",
                    description="No hay bumps registrados aún en este servidor.",
                    color=EMBED_COLOR
                )
                embed.add_field(
                    name="💡 ¿Cómo empezar?",
                    value=f"• Ve a <#{CHANNEL_ID}> y usa `/bump`\n"
                          f"• El sistema registrará automáticamente tus bumps\n"
                          f"• Usa `!help_bumps` para más información",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            top = "\n".join(
                f"**{i+1}.** <@{uid}> — **{count}** bumps"
                for i, (uid, count) in enumerate(bumps[:10])
            )

            embed = discord.Embed(
                title="🏆 Clasificación de Bumps",
                description=top,
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Mostrando top {min(len(bumps), 10)} de {len(bumps)} usuarios")
            
            # Agregar posición del usuario actual si no está en el top 10
            user_bumps = await get_bumps(ctx.author.id, ctx.guild.id)
            if user_bumps > 0:
                # Encontrar posición del usuario
                user_position = None
                for i, (uid, _) in enumerate(bumps, 1):
                    if uid == ctx.author.id:
                        user_position = i
                        break
                
                if user_position and user_position > 10:
                    embed.add_field(
                        name="📍 Tu posición",
                        value=f"**#{user_position}** con **{user_bumps}** bumps",
                        inline=False
                    )
                elif user_position and user_position <= 10:
                    embed.add_field(
                        name="📍 Tu posición",
                        value=f"Apareces en el ranking arriba ⬆️",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            print(f"[BUMP DEBUG] Clasificación mostrada con {len(bumps)} usuarios")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error en clasificacion: {e}")
            await ctx.send("❌ Error obteniendo clasificación. Intenta de nuevo.")

    # Alias para el comando clasificacion (mantener compatibilidad)
    @commands.command(name="bumprank")
    async def bump_rank(self, ctx: commands.Context):
        """Alias para el comando clasificacion"""
        await self.clasificacion(ctx)

    # ────────────────────────────────────────
    # Comando de debug
    # ────────────────────────────────────────
    @commands.command(name="debugbump")
    async def debug_bump(self, ctx: commands.Context):
        """Muestra información de debug del sistema de bumps (solo administradores)"""
        
        # Verificar permisos
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Solo administradores pueden usar este comando.")
            return
        
        embed = discord.Embed(
            title="🔧 Debug del Sistema de Bumps",
            color=EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Información de configuración
        embed.add_field(
            name="⚙️ Configuración",
            value=f"**Canal:** <#{CHANNEL_ID}>\n"
                  f"**Disboard ID:** {DISBOARD_BOT_ID}\n"
                  f"**Rol a mencionar:** <@&{ROLE_ID_TO_PING}>\n"
                  f"**Countdown:** {COUNTDOWN} segundos",
            inline=False
        )
        
        # Estado actual
        pending_count = len(self.pending_bumps)
        active_tasks = len([t for t in self.tasks.values() if not t.done()])
        
        embed.add_field(
            name="📊 Estado Actual",
            value=f"**Bumps pendientes:** {pending_count}\n"
                  f"**Recordatorios activos:** {active_tasks}\n"
                  f"**Guild ID:** {ctx.guild.id}",
            inline=False
        )
        
        # Verificar permisos del bot
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel:
            perms = channel.permissions_for(channel.guild.me)
            perms_status = (
                f"**Leer mensajes:** {'✅' if perms.read_messages else '❌'}\n"
                f"**Enviar mensajes:** {'✅' if perms.send_messages else '❌'}\n"
                f"**Eliminar mensajes:** {'✅' if perms.manage_messages else '❌'}\n"
                f"**Usar embeds:** {'✅' if perms.embed_links else '❌'}\n"
                f"**Mencionar roles:** {'✅' if perms.mention_everyone else '❌'}"
            )
        else:
            perms_status = "❌ Canal no encontrado"
        
        embed.add_field(
            name="🔍 Permisos del Bot",
            value=perms_status,
            inline=False
        )
        
        # Debug de pending bumps
        if self.pending_bumps:
            pending_info = "\n".join(
                f"Guild {guild_id}: Usuario {user_id}"
                for guild_id, user_id in self.pending_bumps.items()
            )
            embed.add_field(
                name="⏳ Bumps Pendientes",
                value=f"```{pending_info}```",
                inline=False
            )
        
        await ctx.send(embed=embed)

    # ────────────────────────────────────────
    # Comando de test
    # ────────────────────────────────────────
    @commands.command(name="testbump", aliases=["tbump", "btest"])
    async def test_bump(self, ctx: commands.Context):
        """Comando de test para simular un bump (solo administradores)"""
        
        # Verificar permisos manualmente
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los administradores pueden usar este comando.",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Sugerencia",
                value="Usa `!help_bumps` para ver los comandos disponibles para ti.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
            
        # Verificar que estamos en el canal correcto
        if ctx.channel.id != CHANNEL_ID:
            embed = discord.Embed(
                title="⚠️ Canal incorrecto",
                description=f"Este comando solo funciona en <#{CHANNEL_ID}>",
                color=0xffa500
            )
            await ctx.send(embed=embed)
            return
            
        # Simular un bump exitoso
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        try:
            # Registrar el bump de prueba
            total = await add_bump(user_id, guild_id)
            
            # Enviar mensaje de confirmación
            thanks = discord.Embed(
                description=(
                    "🧪 **¡Test de bump exitoso!**\n"
                    f"💖 Simulando bump para <@{user_id}>.\n"
                    f"🌟 Total de bumps: **{total}** (incluyendo este test).\n\n"
                    "*⚠️ Este es un bump de prueba*"
                ),
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=thanks)
            
            # Cancelar tarea previa si existe y crear nueva (con countdown reducido para test)
            if task := self.tasks.get(guild_id):
                task.cancel()
            
            # Crear tarea de recordatorio de prueba (30 segundos para test)
            self.tasks[guild_id] = self.bot.loop.create_task(self._recordatorio_test(ctx.channel))
            
            await ctx.send("✅ **Test iniciado** - Recordatorio en 30 segundos")
            print(f"[BUMP DEBUG] Test bump ejecutado por {user_id}")
            
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error en test bump: {e}")
            await ctx.send(f"❌ Error ejecutando test: {str(e)}")

    async def _recordatorio_test(self, channel: discord.TextChannel):
        """Recordatorio de prueba con tiempo reducido"""
        try:
            print(f"[BUMP DEBUG] Test recordatorio iniciado, esperando 30 segundos...")
            await asyncio.sleep(30)  # 30 segundos para test
            print(f"[BUMP DEBUG] Test recordatorio - tiempo completado")
        except asyncio.CancelledError:
            print(f"[BUMP DEBUG] Test recordatorio cancelado")
            return

        try:
            role = channel.guild.get_role(ROLE_ID_TO_PING)
            mention = role.mention if role else "@here"

            embed = discord.Embed(
                description=(
                    "🧪 **¡Test de recordatorio!**\n"
                    "🕐 Este sería el momento de hacer un bump real.\n"
                    "Utiliza **/bump** para apoyar al servidor.\n\n"
                    "*⚠️ Este es un recordatorio de prueba*"
                ),
                color=0xffa500,  # Color naranja para distinguir que es test
                timestamp=datetime.now(timezone.utc)
            )
            await channel.send(content=f"{mention} (TEST)", embed=embed)
            print(f"[BUMP DEBUG] ✅ Test recordatorio enviado")
        except Exception as e:
            print(f"[BUMP DEBUG] ❌ Error en test recordatorio: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print("[BumpTracker] Módulo de bumps listo y funcionando")
        print(f"[BumpTracker] Canal configurado: {CHANNEL_ID}")
        print(f"[BumpTracker] Disboard Bot ID: {DISBOARD_BOT_ID}")
        print(f"[BumpTracker] Rol a mencionar: {ROLE_ID_TO_PING}")
        
        # Verificar que el bot tenga acceso al canal
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel:
            permissions = channel.permissions_for(channel.guild.me)
            print(f"[BumpTracker] Permisos en canal:")
            print(f"  - Leer mensajes: {permissions.read_messages}")
            print(f"  - Enviar mensajes: {permissions.send_messages}")
            print(f"  - Eliminar mensajes: {permissions.manage_messages}")
            print(f"  - Usar embeds: {permissions.embed_links}")
            print(f"  - Mencionar roles: {permissions.mention_everyone}")
        else:
            print(f"[BumpTracker] ❌ No se pudo encontrar el canal {CHANNEL_ID}")


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpTracker(bot))