import discord
from discord.ext import commands

# Diccionario con categorías y sus comandos
CATEGORIAS = {
    "Niveles": [
        ":xp",
        ":top",
        ":top_semanal",
        ":top_mensual"
    ],
    "Bumps": [
        ":bumpstats",
        ":clasificacion"
    ],
    "Economía": [
        ":saldo",
        ":inventario",
        ":tienda",
        ':comprar "nombre"',
        ':use "nombre"',
        ":transferir @usuario monto"
    ],
    "Invitaciones": [
        ":user_invites [usuario]",
        ":who_invited [usuario]",
        ":invites_leaderboard",
        ":my_rank",
        ":top_invites"
    ]
}

class CategoriaSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat, description=f"Ver comandos de {cat}")
            for cat in CATEGORIAS.keys()
        ]
        super().__init__(
            placeholder="Selecciona una categoría...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        comandos = "\n".join(CATEGORIAS[categoria])
        embed = discord.Embed(
            title=f"📜 Comandos — {categoria}",
            description=f"```{comandos}```",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self.view)

class CategoriaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoriaSelect())

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="comandos")
    async def comandos(self, ctx):
        embed = discord.Embed(
            title="📜 Comandos",
            description="Elija una categoría en el menú de abajo para ver sus comandos.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=CategoriaView())

async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))
