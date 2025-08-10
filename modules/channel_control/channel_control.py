import discord
from discord.ext import commands

class ChannelControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Placeholder - puedes agregar comandos aquí después
    @commands.command(name="channel_test")
    @commands.has_permissions(administrator=True)
    async def channel_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Channel funcionando",
            description="El módulo de control de canales está cargado correctamente.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelControl(bot))