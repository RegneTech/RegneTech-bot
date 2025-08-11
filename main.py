import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Verificar que el token existe
if not TOKEN:
    print("❌ Error: No se encontró DISCORD_TOKEN en el archivo .env")
    exit(1)

# Intents (permisos de eventos de Discord)
import discord
intents = discord.Intents.default()
intents.members = True      
intents.message_content = True   
intents.invites = True 

# Crear instancia del bot
bot = commands.Bot(command_prefix="!", intents=intents)

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
]

# Cargar módulos automáticamente (ASYNC)
async def load_cogs():
    """Carga todos los módulos del bot con manejo de errores individual"""
    loaded_count = 0
    failed_count = 0
    
    for module in MODULES:
        try:
            await bot.load_extension(module)
            module_name = module.split('.')[-1]  # Obtener solo el nombre del módulo
            print(f"✅ Módulo '{module_name}' cargado correctamente")
            loaded_count += 1
        except Exception as e:
            module_name = module.split('.')[-1]
            print(f"❌ Error cargando '{module_name}': {e}")
            failed_count += 1
    
    print(f"\n📊 Resumen de carga: {loaded_count} exitosos, {failed_count} fallidos")
    
    if loaded_count == 0:
        print("⚠️ Advertencia: No se cargó ningún módulo. El bot funcionará con comandos básicos solamente.")

# Comando básico de prueba (siempre disponible)
@bot.command(name="ping")
async def ping(ctx):
    """Comando de prueba básico"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latencia: **{latency}ms**",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name="info")
async def bot_info(ctx):
    """Información básica del bot"""
    embed = discord.Embed(
        title="🤖 Información del Bot",
        description="Bot multiusos para Discord",
        color=0x00ffff
    )
    embed.add_field(name="Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="Usuarios", value=len(bot.users), inline=True)
    embed.add_field(name="Comandos", value=len(bot.commands), inline=True)
    embed.set_footer(text=f"Bot: {bot.user.name}")
    await ctx.send(embed=embed)

# Comando para recargar módulos (solo para desarrollo)
@bot.command(name="reload")
@commands.is_owner()
async def reload_cogs(ctx):
    """Recarga todos los módulos (solo owner)"""
    await ctx.send("🔄 Recargando módulos...")
    
    # Descargar módulos existentes
    for module in list(bot.extensions.keys()):
        try:
            await bot.unload_extension(module)
        except:
            pass
    
    # Cargar módulos nuevamente
    await load_cogs()
    await ctx.send("✅ Módulos recargados")

# Manejo de errores globales
@bot.event
async def on_command_error(ctx, error):
    """Manejo global de errores de comandos"""
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Comando no encontrado",
            description=f"El comando `{ctx.invoked_with}` no existe.\nUsa `!comandos` para ver comandos disponibles.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="🚫 Sin permisos",
            description="No tienes permisos para usar este comando.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Comando en cooldown",
            description=f"Espera {error.retry_after:.1f} segundos antes de usar este comando otra vez.",
            color=0xffa500
        )
        await ctx.send(embed=embed)
    
    else:
        # Log de errores no manejados
        print(f"Error no manejado en comando {ctx.command}: {error}")
        embed = discord.Embed(
            title="⚠️ Error interno",
            description="Ocurrió un error interno. Contacta al administrador.",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Evento cuando el bot se conecta"""
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📊 Conectado a {len(bot.guilds)} servidores")
    print(f"👥 Alcance: {len(bot.users)} usuarios")
    print("─" * 50)
    
    # Cargar módulos después de que el bot esté listo
    await load_cogs()
    
    print("─" * 50)
    print("🚀 Bot listo para usar!")

@bot.event
async def on_guild_join(guild):
    """Evento cuando el bot se une a un servidor"""
    print(f"✅ Bot añadido al servidor: {guild.name} (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    """Evento cuando el bot es removido de un servidor"""
    print(f"❌ Bot removido del servidor: {guild.name} (ID: {guild.id})")

# Función principal asíncrona
async def main():
    """Función principal del bot"""
    print("🤖 Iniciando bot...")
    print("─" * 50)

    try:
        # 🔹 Conectar a la base de datos antes de iniciar el bot
        await connect_db()
        print("✅ Base de datos conectada")

        async with bot:
            await bot.start(TOKEN)

    except discord.LoginFailure:
        print("❌ Error: Token de Discord inválido")
    except discord.HTTPException as e:
        print(f"❌ Error de conexión HTTP: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        print("👋 Bot desconectado")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Programa interrumpido")
    except Exception as e:
        print(f"❌ Error crítico: {e}")