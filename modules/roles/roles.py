import discord
from discord.ext import commands

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Placeholder - puedes agregar comandos aquí después
    @commands.command(name="roles_test")
    @commands.has_permissions(administrator=True)
    async def roles_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Roles funcionando",
            description="El módulo de roles está cargado correctamente.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))