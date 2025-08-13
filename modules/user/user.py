import discord
from discord.ext import commands

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Placeholder - puedes agregar comandos aquí después
    @commands.command(name="user_test")
    @commands.has_permissions(administrator=True)
    async def user_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo User funcionando",
            description="El módulo de Users está cargado correctamente.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))