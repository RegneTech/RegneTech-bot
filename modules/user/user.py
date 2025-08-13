import discord
from discord.ext import commands

# Diccionario con categorías y comandos
CATEGORIAS = {
    "📊 Niveles": {
        "emoji": "📊",
        "descripcion": "Sistema de experiencia y rankings",
        "color": 0x00ff00,
        "comandos": [
            {
                "comando": "!xp [@usuario]",
                "descripcion": "Ver tu experiencia actual o la de otro usuario",
                "uso": "`!xp` o `!xp @usuario`"
            },
            {
                "comando": "!top [página]",
                "descripcion": "Ranking global de usuarios por XP",
                "uso": "`!top` o `!top 2`"
            },
            {
                "comando": "!top_semanal",
                "descripcion": "Top usuarios con más XP esta semana",
                "uso": "`!top_semanal`"
            },
            {
                "comando": "!top_mensual",
                "descripcion": "Top usuarios con más XP este mes",
                "uso": "`!top_mensual`"
            }
        ]
    },
    "🚀 Bumps": {
        "emoji": "🚀",
        "descripcion": "Estadísticas y rankings de bumps",
        "color": 0xff6b35,
        "comandos": [
            {
                "comando": "!bumpstats [@usuario]",
                "descripcion": "Ver estadísticas de bumps realizados",
                "uso": "`!bumpstats` o `!bumpstats @usuario`"
            },
            {
                "comando": "!clasificacion",
                "descripcion": "Ranking de usuarios por bumps realizados",
                "uso": "`!clasificacion`"
            }
        ]
    },
    "💰 Economía": {
        "emoji": "💰",
        "descripcion": "Sistema económico del servidor",
        "color": 0xffd700,
        "comandos": [
            {
                "comando": "!saldo [@usuario]",
                "descripcion": "Consultar tu balance o el de otro usuario",
                "uso": "`!saldo` o `!saldo @usuario`"
            },
            {
                "comando": "!inventario [@usuario]",
                "descripcion": "Ver los items que posees",
                "uso": "`!inventario` o `!inventario @usuario`"
            },
            {
                "comando": "!tienda [página]",
                "descripcion": "Explorar la tienda de items disponibles",
                "uso": "`!tienda` o `!tienda 2`"
            },
            {
                "comando": "!comprar \"nombre\"",
                "descripcion": "Comprar un item específico de la tienda",
                "uso": "`!comprar \"Poción de Vida\"`"
            },
            {
                "comando": "!use \"nombre\"",
                "descripcion": "Usar un item de tu inventario",
                "uso": "`!use \"Poción de Vida\"`"
            },
            {
                "comando": "!transferir @usuario monto",
                "descripcion": "Transferir dinero a otro usuario",
                "uso": "`!transferir @usuario 1000`"
            }
        ]
    },
    "📨 Invitaciones": {
        "emoji": "📨",
        "descripcion": "Sistema de invitaciones y rankings",
        "color": 0x9b59b6,
        "comandos": [
            {
                "comando": "!user_invites [@usuario]",
                "descripcion": "Ver invitaciones realizadas por un usuario",
                "uso": "`!user_invites` o `!user_invites @usuario`"
            },
            {
                "comando": "!who_invited [@usuario]",
                "descripcion": "Ver quién invitó a un usuario al servidor",
                "uso": "`!who_invited @usuario`"
            },
            {
                "comando": "!invites_leaderboard",
                "descripcion": "Ranking completo de invitaciones",
                "uso": "`!invites_leaderboard`"
            },
            {
                "comando": "!my_rank",
                "descripcion": "Tu posición en el ranking de invitaciones",
                "uso": "`!my_rank`"
            },
            {
                "comando": "!top_invites [cantidad]",
                "descripcion": "Top usuarios con más invitaciones",
                "uso": "`!top_invites` o `!top_invites 15`"
            }
        ]
    }
}

class ComandoSelect(discord.ui.Select):
    def __init__(self, categoria_data, categoria_nombre):
        self.categoria_data = categoria_data
        self.categoria_nombre = categoria_nombre
        
        options = []
        for i, cmd in enumerate(categoria_data["comandos"][:25]):
            options.append(
                discord.SelectOption(
                    label=cmd["comando"],
                    description=cmd["descripcion"][:100],
                    value=str(i),
                    emoji="⚡"
                )
            )
        
        super().__init__(
            placeholder="Selecciona un comando...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            index = int(self.values[0])
            cmd = self.categoria_data["comandos"][index]
            
            embed = discord.Embed(
                title=f"{cmd['comando']}",
                description=cmd['descripcion'],
                color=self.categoria_data["color"]
            )
            embed.add_field(
                name="Uso:",
                value=cmd['uso'],
                inline=False
            )
            
            view = ComandoDetalleView(self.categoria_nombre, self.categoria_data)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ComandoDetalleView(discord.ui.View):
    def __init__(self, categoria_nombre, categoria_data):
        super().__init__(timeout=300)
        self.categoria_nombre = categoria_nombre
        self.categoria_data = categoria_data
    
    @discord.ui.button(label="← Volver", style=discord.ButtonStyle.secondary)
    async def volver_categoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = self.crear_embed_categoria()
            view = CategoriaDetalleView(self.categoria_nombre, self.categoria_data)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @discord.ui.button(label="🏠 Inicio", style=discord.ButtonStyle.primary)
    async def menu_principal(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="🤖 Comandos",
                description="Selecciona una categoría:",
                color=0x2f3136
            )
            view = CategoriaView()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    def crear_embed_categoria(self):
        comandos_lista = []
        for i, cmd in enumerate(self.categoria_data["comandos"], 1):
            comandos_lista.append(f"`{i}.` **{cmd['comando']}**\n{cmd['descripcion']}")
        
        embed = discord.Embed(
            title=f"{self.categoria_data['emoji']} {self.categoria_nombre}",
            description="\n\n".join(comandos_lista),
            color=self.categoria_data["color"]
        )
        return embed

class CategoriaDetalleView(discord.ui.View):
    def __init__(self, categoria_nombre, categoria_data):
        super().__init__(timeout=300)
        self.categoria_nombre = categoria_nombre
        self.categoria_data = categoria_data
        self.add_item(ComandoSelect(categoria_data, categoria_nombre))
    
    @discord.ui.button(label="🏠 Inicio", style=discord.ButtonStyle.primary)
    async def menu_principal(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="🤖 Comandos",
                description="Selecciona una categoría:",
                color=0x2f3136
            )
            view = CategoriaView()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class CategoriaSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for cat_name, cat_data in CATEGORIAS.items():
            options.append(
                discord.SelectOption(
                    label=cat_name.split(" ", 1)[1],
                    description=f"{len(cat_data['comandos'])} comandos",
                    value=cat_name,
                    emoji=cat_data["emoji"]
                )
            )
        
        super().__init__(
            placeholder="Categorías",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            categoria_nombre = self.values[0]
            categoria_data = CATEGORIAS[categoria_nombre]
            
            comandos_lista = []
            for i, cmd in enumerate(categoria_data["comandos"], 1):
                comandos_lista.append(f"`{i}.` **{cmd['comando']}**\n{cmd['descripcion']}")
            
            embed = discord.Embed(
                title=f"{categoria_data['emoji']} {categoria_nombre}",
                description="\n\n".join(comandos_lista),
                color=categoria_data["color"]
            )
            
            view = CategoriaDetalleView(categoria_nombre, categoria_data)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class CategoriaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)
        self.add_item(CategoriaSelect())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Cog User inicializado")
    
    @commands.command(name="menu", aliases=["comandos", "ayuda", "commands", "cmds"])
    async def menu_comandos(self, ctx):
        """Menú de comandos interactivo"""
        
        try:
            embed = discord.Embed(
                title="🤖 Comandos",
                description="Selecciona una categoría:",
                color=0x2f3136
            )
            
            await ctx.send(embed=embed, view=CategoriaView())
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="test")
    async def test_comando(self, ctx):
        """Comando de prueba"""
        await ctx.send("✅ Bot funcionando")

async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))
    print("✅ Cog User cargado")

async def teardown(bot: commands.Bot):
    print("❌ Cog User descargado")