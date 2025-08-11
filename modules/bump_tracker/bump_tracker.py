import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone

# Importar funciones de base de datos
import database

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

    # ────────────────────────────────
    # Comando de ayuda para bumps
    # ────────────────────────────────
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
                  "  *(Solo funciona en el canal de bumps)*",
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
        if message.channel.id != CHANNEL_ID:
            return

        if message.author.id == DISBOARD_BOT_ID:
            await self.disboard_only_bump(message)
            return

        if message.content.strip().lower() == "/bump":
            self.pending_bumps[message.guild.id] = message.author.id

    # ───────────── procesamiento de mensajes de DISBOARD ─────────────
    async def disboard_only_bump(self, message: discord.Message):
        if message.interaction:
            cmd = (message.interaction.name or "").lower()
            user_id = message.interaction.user.id

            if cmd != "bump":
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                return

            self.pending_bumps[message.guild.id] = user_id

            if not (message.content or message.embeds):
                return

        if not message.embeds:
            return

        embed = message.embeds[0]
        text = f"{embed.title or ''} {embed.description or ''}".lower()

        is_success = "bump done" in text or "¡hecho!" in text
        if not is_success:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            return

        guild_id = message.guild.id
        if guild_id not in self.pending_bumps:
            return

        user_id = self.pending_bumps.pop(guild_id)

        # ── Agradecimiento y contador (DB) ──
        total = await add_bump(user_id, guild_id)

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

        # Cancelar tarea previa si existe y crear nueva
        if task := self.tasks.get(guild_id):
            task.cancel()
        self.tasks[guild_id] = self.bot.loop.create_task(self._recordatorio(message.channel))

    async def _recordatorio(self, channel: discord.TextChannel):
        try:
            await asyncio.sleep(COUNTDOWN)
        except asyncio.CancelledError:
            return

        role = channel.guild.get_role(ROLE_ID_TO_PING)
        mention = role.mention if role else "@here"

        embed = discord.Embed(
            description=(
                "🕒 **¡Es momento de hacer un bump!**\n"
                "Utiliza **/bump** para apoyar al servidor.\n\n"
                "*Sistema de recordatorio de bump*"
            ),
            color=EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        await channel.send(content=mention, embed=embed)

    # ────────────────────────────────
    # Comando: ver estadísticas personales de bumps
    # ────────────────────────────────
    @commands.command(name="bumpstats")
    async def bump_stats(self, ctx: commands.Context):
        """Muestra las estadísticas personales de bumps del usuario"""
        bumps = await get_bumps(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Tus estadísticas de Bump",
            description=f"Has realizado **{bumps}** bumps en este servidor.",
            color=EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        # Agregar información adicional
        embed.add_field(
            name="💡 Información",
            value=f"• Usa `!clasificacion` para ver el ranking completo\n"
                  f"• Usa `!help_bumps` para ver todos los comandos disponibles",
            inline=False
        )
        
        await ctx.send(embed=embed)

    # ────────────────────────────────
    # Comando: ranking completo de bumps
    # ────────────────────────────────
    @commands.command(name="clasificacion")
    async def clasificacion(self, ctx):
        """Muestra el ranking de usuarios por cantidad de bumps"""
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
            embed.add_field(
                name="📍 Tu posición",
                value=f"Tienes **{user_bumps}** bumps registrados",
                inline=False
            )
        
        await ctx.send(embed=embed)

    # Alias para el comando clasificacion (mantener compatibilidad)
    @commands.command(name="bumprank")
    async def bump_rank(self, ctx: commands.Context):
        """Alias para el comando clasificacion"""
        await self.clasificacion(ctx)

    # ────────────────────────────────
    # Comando de test
    # ────────────────────────────────
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

    async def _recordatorio_test(self, channel: discord.TextChannel):
        """Recordatorio de prueba con tiempo reducido"""
        try:
            await asyncio.sleep(30)  # 30 segundos para test
        except asyncio.CancelledError:
            return

        role = channel.guild.get_role(ROLE_ID_TO_PING)
        mention = role.mention if role else "@here"

        embed = discord.Embed(
            description=(
                "🧪 **¡Test de recordatorio!**\n"
                "🕒 Este sería el momento de hacer un bump real.\n"
                "Utiliza **/bump** para apoyar al servidor.\n\n"
                "*⚠️ Este es un recordatorio de prueba*"
            ),
            color=0xffa500,  # Color naranja para distinguir que es test
            timestamp=datetime.now(timezone.utc)
        )
        await channel.send(content=f"{mention} (TEST)", embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[BumpTracker] Módulo de bumps listo y funcionando")


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpTracker(bot))