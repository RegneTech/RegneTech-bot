import os
import asyncio
import logging
import sys
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from database import connect_db
import discord

# Configuración de logging
def setup_logging():
    """Configurar sistema de logging"""
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    # Formato de logs
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # Handler para archivo
    file_handler = logging.FileHandler(
        f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    
    # Agregar handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Configurar logging de discord.py
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Configurar logging
logger = setup_logging()

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Verificación de token
if not TOKEN:
    logger.critical("❌ Error: No se encontró DISCORD_TOKEN en el archivo .env")
    sys.exit(1)

# Configuración de intents
intents = discord.Intents.default()
intents.members = True      
intents.message_content = True   
intents.invites = True 
intents.guilds = True
intents.guild_messages = True

# Lista de módulos a cargar
MODULES = [
    "modules.admin.admin",
    "modules.bump_tracker.bump_tracker",
    "modules.channel_control.channel_control", 
    "modules.economia.resenas",
    "modules.economia.economia",
    "modules.welcome.welcome",
    "modules.levels.levels",
    "modules.invites.invites",
    "modules.tickets.tickets",
    "modules.beginning.beginning",
    "modules.economia.sorteos",
    "modules.user.user",
    "modules.admin.partner",
    "modules.cuentas.cuentas",
]

class DiscordBot(commands.Bot):
    """Bot personalizado con funcionalidades extendidas"""
    
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # Deshabilitar comando help por defecto
            case_insensitive=True,
            strip_after_prefix=True
        )
        self.cogs_loaded = False
        self.start_time = datetime.now()
        
    async def setup_hook(self):
        """Configuración inicial del bot (se ejecuta una sola vez)"""
        logger.info("🔧 Ejecutando setup inicial...")
        await self.load_cogs()
        logger.info("✅ Setup completado")
        
    async def load_cogs(self):
        """Carga todos los módulos del bot con manejo de errores individual"""
        if self.cogs_loaded:
            logger.info("⚠️ Los cogs ya están cargados, saltando...")
            return
            
        logger.info("📦 Iniciando carga de módulos...")
        loaded_count = 0
        failed_count = 0
        
        for module in MODULES:
            try:
                await self.load_extension(module)
                module_name = module.split('.')[-1]
                logger.info(f"✅ Módulo '{module_name}' cargado correctamente")
                loaded_count += 1
            except Exception as e:
                module_name = module.split('.')[-1]
                logger.error(f"❌ Error cargando '{module_name}': {e}")
                failed_count += 1
        
        logger.info(f"📊 Resumen de carga: {loaded_count} exitosos, {failed_count} fallidos")
        
        if loaded_count == 0:
            logger.warning("⚠️ No se cargó ningún módulo. El bot funcionará con comandos básicos solamente.")
        
        self.cogs_loaded = True
    
    async def on_ready(self):
        """Evento cuando el bot está completamente listo"""
        logger.info("=" * 60)
        logger.info(f"✅ Bot conectado como {self.user}")
        logger.info(f"📊 Conectado a {len(self.guilds)} servidores")
        logger.info(f"👥 Alcance: {len(self.users)} usuarios")
        logger.info(f"🔧 Discord.py versión: {discord.__version__}")
        logger.info(f"⏰ Tiempo de inicio: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Establecer estado del bot
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servidores | !help"
        )
        await self.change_presence(activity=activity)
        
        logger.info("=" * 60)
        logger.info("🚀 Bot listo para usar!")
    
    async def on_guild_join(self, guild):
        """Evento cuando el bot se une a un servidor"""
        logger.info(f"✅ Bot añadido al servidor: {guild.name} (ID: {guild.id}) - {guild.member_count} miembros")
        
        # Actualizar estado
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servidores | !help"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_remove(self, guild):
        """Evento cuando el bot es removido de un servidor"""
        logger.info(f"❌ Bot removido del servidor: {guild.name} (ID: {guild.id})")
        
        # Actualizar estado
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servidores | !help"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Manejo global de errores de comandos"""
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❌ Comando no encontrado",
                description=f"El comando `{ctx.invoked_with}` no existe.\nUsa `!help` para ver comandos disponibles.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🚫 Sin permisos",
                description="No tienes permisos para usar este comando.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Comando en cooldown",
                description=f"Espera {error.retry_after:.1f} segundos antes de usar este comando otra vez.",
                color=0xffa500
            )
            await ctx.send(embed=embed, delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Argumento faltante",
                description=f"Faltan argumentos para el comando `{ctx.command}`.\nUsa `!help {ctx.command}` para más información.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Argumento inválido",
                description=f"Argumento inválido para el comando `{ctx.command}`.\nUsa `!help {ctx.command}` para más información.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            logger.error(f"Error no manejado en comando {ctx.command}: {error}", exc_info=True)
            embed = discord.Embed(
                title="⚠️ Error interno",
                description="Ocurrió un error interno. El error ha sido registrado.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)

# Crear instancia del bot
bot = DiscordBot()

# ========== COMANDOS BÁSICOS ==========

@bot.command(name="ping", help="Muestra la latencia del bot")
async def ping(ctx):
    """Comando para verificar la latencia del bot"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latencia: **{latency}ms**",
        color=0x00ff00
    )
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="info", aliases=["botinfo"], help="Información del bot")
async def bot_info(ctx):
    """Información detallada del bot"""
    uptime = datetime.now() - bot.start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    embed = discord.Embed(
        title="🤖 Información del Bot",
        description="Bot multiusos para Discord",
        color=0x00ffff
    )
    embed.add_field(name="📊 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Usuarios", value=len(bot.users), inline=True)
    embed.add_field(name="⚡ Comandos", value=len(bot.commands), inline=True)
    embed.add_field(name="🔧 Módulos", value=len(bot.cogs), inline=True)
    embed.add_field(name="📶 Latencia", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="⏰ Uptime", value=f"{days}d {hours}h {minutes}m", inline=True)
    embed.set_footer(text=f"Bot: {bot.user.name} | Discord.py {discord.__version__}")
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await ctx.send(embed=embed)

@bot.command(name="help", aliases=["ayuda"], help="Muestra ayuda de comandos")
async def help_command(ctx, command: str = None):
    """Comando de ayuda personalizado"""
    if command:
        # Ayuda para comando específico
        cmd = bot.get_command(command)
        if cmd:
            embed = discord.Embed(
                title=f"📖 Ayuda: {cmd.name}",
                description=cmd.help or "Sin descripción disponible",
                color=0x0099ff
            )
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=False)
            embed.add_field(name="Uso", value=f"`!{cmd.name} {cmd.signature}`", inline=False)
        else:
            embed = discord.Embed(
                title="❌ Comando no encontrado",
                description=f"No existe el comando `{command}`",
                color=0xff0000
            )
    else:
        # Lista de comandos básicos
        embed = discord.Embed(
            title="📚 Comandos Disponibles",
            description="Lista de comandos básicos del bot",
            color=0x0099ff
        )
        
        basic_commands = ["ping", "info", "help"]
        embed.add_field(
            name="🔧 Básicos",
            value="`" + "`, `".join(basic_commands) + "`",
            inline=False
        )
        
        if bot.cogs:
            cog_list = list(bot.cogs.keys())[:5]  # Primeros 5 módulos
            embed.add_field(
                name="📦 Módulos Cargados",
                value="`" + "`, `".join(cog_list) + "`" + (f" y {len(bot.cogs) - 5} más..." if len(bot.cogs) > 5 else ""),
                inline=False
            )
        
        embed.add_field(
            name="💡 Tip",
            value="Usa `!help <comando>` para obtener ayuda específica de un comando",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="reload", help="Recarga todos los módulos")
@commands.is_owner()
async def reload_cogs(ctx):
    """Recargar todos los módulos (solo owner)"""
    await ctx.send("🔄 Recargando módulos...")
    
    # Descargar módulos existentes
    for module in list(bot.extensions.keys()):
        try:
            await bot.unload_extension(module)
            logger.info(f"🔄 Módulo '{module.split('.')[-1]}' descargado")
        except Exception as e:
            logger.error(f"❌ Error descargando {module}: {e}")
    
    # Recargar módulos
    bot.cogs_loaded = False
    await bot.load_cogs()
    
    embed = discord.Embed(
        title="✅ Recarga completa",
        description=f"Módulos recargados: {len(bot.cogs)}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name="shutdown", aliases=["stop"], help="Apaga el bot")
@commands.is_owner()
async def shutdown(ctx):
    """Apagar el bot de forma segura (solo owner)"""
    embed = discord.Embed(
        title="👋 Apagando bot...",
        description="El bot se desconectará en breve.",
        color=0xffa500
    )
    await ctx.send(embed=embed)
    logger.info("🛑 Bot apagado por comando del owner")
    await bot.close()

# ========== FUNCIÓN PRINCIPAL ==========

async def main():
    """Función principal del bot"""
    logger.info("🤖 Iniciando bot...")
    logger.info("=" * 60)

    try:
        # Conectar a base de datos
        logger.info("🔌 Conectando a base de datos...")
        db_success = await connect_db()
        if db_success:
            logger.info("✅ Base de datos conectada")
        else:
            logger.warning("⚠️ Base de datos no disponible, continuando sin ella")

        # Iniciar bot
        logger.info("🚀 Iniciando conexión con Discord...")
        async with bot:
            await bot.start(TOKEN)
            
    except discord.LoginFailure:
        logger.critical("❌ Error: Token de Discord inválido")
        sys.exit(1)
    except discord.HTTPException as e:
        logger.critical(f"❌ Error de conexión HTTP: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido por el usuario")
    except Exception as e:
        logger.critical(f"❌ Error inesperado: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Bot desconectado")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Programa interrumpido")
    except Exception as e:
        logger.critical(f"❌ Error crítico: {e}", exc_info=True)
        sys.exit(1)