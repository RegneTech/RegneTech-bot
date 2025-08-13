import discord
from discord.ext import commands

# Diccionario mejorado con categorías, comandos y descripciones
CATEGORIAS = {
    "📊 Niveles": {
        "emoji": "📊",
        "descripcion": "Sistema de experiencia y rankings",
        "color": 0x00ff00,
        "comandos": [
            {
                "comando": ":xp [@usuario]",
                "descripcion": "Ver tu experiencia actual o la de otro usuario",
                "uso": "`:xp` o `:xp @usuario`"
            },
            {
                "comando": ":top [página]",
                "descripcion": "Ranking global de usuarios por XP",
                "uso": "`:top` o `:top 2`"
            },
            {
                "comando": ":top_semanal",
                "descripcion": "Top usuarios con más XP esta semana",
                "uso": "`:top_semanal`"
            },
            {
                "comando": ":top_mensual",
                "descripcion": "Top usuarios con más XP este mes",
                "uso": "`:top_mensual`"
            }
        ]
    },
    "🚀 Bumps": {
        "emoji": "🚀",
        "descripcion": "Estadísticas y rankings de bumps",
        "color": 0xff6b35,
        "comandos": [
            {
                "comando": ":bumpstats [@usuario]",
                "descripcion": "Ver estadísticas de bumps realizados",
                "uso": "`:bumpstats` o `:bumpstats @usuario`"
            },
            {
                "comando": ":clasificacion",
                "descripción": "Ranking de usuarios por bumps realizados",
                "uso": "`:clasificacion`"
            }
        ]
    },
    "💰 Economía": {
        "emoji": "💰",
        "descripcion": "Sistema económico del servidor",
        "color": 0xffd700,
        "comandos": [
            {
                "comando": ":saldo [@usuario]",
                "descripcion": "Consultar tu balance o el de otro usuario",
                "uso": "`:saldo` o `:saldo @usuario`"
            },
            {
                "comando": ":inventario [@usuario]",
                "descripcion": "Ver los items que posees",
                "uso": "`:inventario` o `:inventario @usuario`"
            },
            {
                "comando": ":tienda [página]",
                "descripcion": "Explorar la tienda de items disponibles",
                "uso": "`:tienda` o `:tienda 2`"
            },
            {
                "comando": ":comprar \"nombre\"",
                "descripcion": "Comprar un item específico de la tienda",
                "uso": "`:comprar \"Poción de Vida\"`"
            },
            {
                "comando": ":use \"nombre\"",
                "descripcion": "Usar un item de tu inventario",
                "uso": "`:use \"Poción de Vida\"`"
            },
            {
                "comando": ":transferir @usuario monto",
                "descripcion": "Transferir dinero a otro usuario",
                "uso": "`:transferir @usuario 1000`"
            }
        ]
    },
    "📨 Invitaciones": {
        "emoji": "📨",
        "descripcion": "Sistema de invitaciones y rankings",
        "color": 0x9b59b6,
        "comandos": [
            {
                "comando": ":user_invites [@usuario]",
                "descripcion": "Ver invitaciones realizadas por un usuario",
                "uso": "`:user_invites` o `:user_invites @usuario`"
            },
            {
                "comando": ":who_invited [@usuario]",
                "descripcion": "Ver quién invitó a un usuario al servidor",
                "uso": "`:who_invited @usuario`"
            },
            {
                "comando": ":invites_leaderboard",
                "descripcion": "Ranking completo de invitaciones",
                "uso": "`:invites_leaderboard`"
            },
            {
                "comando": ":my_rank",
                "descripcion": "Tu posición en el ranking de invitaciones",
                "uso": "`:my_rank`"
            },
            {
                "comando": ":top_invites [cantidad]",
                "descripcion": "Top usuarios con más invitaciones",
                "uso": "`:top_invites` o `:top_invites 15`"
            }
        ]
    }
}

class ComandoSelect(discord.ui.Select):
    def __init__(self, categoria_data, categoria_nombre):
        self.categoria_data = categoria_data
        self.categoria_nombre = categoria_nombre
        
        options = []
        for i, cmd in enumerate(categoria_data["comandos"][:25]):  # Discord limit
            options.append(
                discord.SelectOption(
                    label=cmd["comando"],
                    description=cmd["descripcion"][:100],  # Discord limit
                    value=str(i),
                    emoji="⚡"
                )
            )
        
        super().__init__(
            placeholder="Selecciona un comando para ver detalles...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        cmd = self.categoria_data["comandos"][index]
        
        embed = discord.Embed(
            title=f"{self.categoria_data['emoji']} Comando: {cmd['comando']}",
            description=f"**📝 Descripción:**\n{cmd['descripcion']}",
            color=self.categoria_data["color"]
        )
        embed.add_field(
            name="💡 Ejemplo de uso:",
            value=f"`{cmd['uso']}`",
            inline=False
        )
        embed.add_field(
            name="📂 Categoría:",
            value=self.categoria_nombre,
            inline=True
        )
        embed.set_footer(text="💡 Los parámetros entre [] son opcionales, entre \"\" son obligatorios")
        
        # Crear vista con botón para volver
        view = ComandoDetalleView(self.categoria_nombre, self.categoria_data)
        await interaction.response.edit_message(embed=embed, view=view)

class ComandoDetalleView(discord.ui.View):
    def __init__(self, categoria_nombre, categoria_data):
        super().__init__(timeout=300)
        self.categoria_nombre = categoria_nombre
        self.categoria_data = categoria_data
    
    @discord.ui.button(label="← Volver a la categoría", style=discord.ButtonStyle.secondary, emoji="🔙")
    async def volver_categoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.crear_embed_categoria()
        view = CategoriaDetalleView(self.categoria_nombre, self.categoria_data)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🏠 Menú Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def menu_principal(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.crear_embed_principal()
        view = CategoriaView()
        await interaction.response.edit_message(embed=embed, view=view)
    
    def crear_embed_categoria(self):
        comandos_lista = []
        for i, cmd in enumerate(self.categoria_data["comandos"], 1):
            comandos_lista.append(f"`{i}.` **{cmd['comando']}**\n   └ {cmd['descripcion']}")
        
        embed = discord.Embed(
            title=f"{self.categoria_data['emoji']} {self.categoria_nombre}",
            description=f"*{self.categoria_data['descripcion']}*\n\n" + "\n\n".join(comandos_lista),
            color=self.categoria_data["color"]
        )
        embed.set_footer(text=f"📋 {len(self.categoria_data['comandos'])} comandos disponibles • Selecciona uno para ver detalles")
        return embed
    
    def crear_embed_principal(self):
        return discord.Embed(
            title="🤖 Centro de Comandos",
            description=(
                "¡Bienvenido al centro de comandos! Aquí encontrarás todas las funcionalidades disponibles.\n\n"
                f"🎯 **Categorías disponibles:** {len(CATEGORIAS)}\n"
                f"⚡ **Total de comandos:** {sum(len(cat['comandos']) for cat in CATEGORIAS.values())}\n\n"
                "**Selecciona una categoría del menú desplegable para explorar:**"
            ),
            color=0x2f3136
        )

class CategoriaDetalleView(discord.ui.View):
    def __init__(self, categoria_nombre, categoria_data):
        super().__init__(timeout=300)
        self.categoria_nombre = categoria_nombre
        self.categoria_data = categoria_data
        self.add_item(ComandoSelect(categoria_data, categoria_nombre))
    
    @discord.ui.button(label="🏠 Menú Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def menu_principal(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🤖 Centro de Comandos",
            description=(
                "¡Bienvenido al centro de comandos! Aquí encontrarás todas las funcionalidades disponibles.\n\n"
                f"🎯 **Categorías disponibles:** {len(CATEGORIAS)}\n"
                f"⚡ **Total de comandos:** {sum(len(cat['comandos']) for cat in CATEGORIAS.values())}\n\n"
                "**Selecciona una categoría del menú desplegable para explorar:**"
            ),
            color=0x2f3136
        )
        view = CategoriaView()
        await interaction.response.edit_message(embed=embed, view=view)

class CategoriaSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for cat_name, cat_data in CATEGORIAS.items():
            options.append(
                discord.SelectOption(
                    label=cat_name.split(" ", 1)[1],  # Quitar emoji del label
                    description=f"{cat_data['descripcion']} • {len(cat_data['comandos'])} comandos",
                    value=cat_name,
                    emoji=cat_data["emoji"]
                )
            )
        
        super().__init__(
            placeholder="🔍 Explora las categorías de comandos...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        categoria_nombre = self.values[0]
        categoria_data = CATEGORIAS[categoria_nombre]
        
        # Crear lista de comandos con numeración
        comandos_lista = []
        for i, cmd in enumerate(categoria_data["comandos"], 1):
            comandos_lista.append(f"`{i}.` **{cmd['comando']}**\n   └ {cmd['descripcion']}")
        
        embed = discord.Embed(
            title=f"{categoria_data['emoji']} {categoria_nombre}",
            description=f"*{categoria_data['descripcion']}*\n\n" + "\n\n".join(comandos_lista),
            color=categoria_data["color"]
        )
        embed.set_footer(text=f"📋 {len(categoria_data['comandos'])} comandos disponibles • Selecciona uno para ver detalles")
        
        view = CategoriaDetalleView(categoria_nombre, categoria_data)
        await interaction.response.edit_message(embed=embed, view=view)

class CategoriaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)  # 10 minutos de timeout
        self.add_item(CategoriaSelect())
    
    @discord.ui.button(label="📚 Guía de Uso", style=discord.ButtonStyle.secondary, emoji="📚")
    async def guia_uso(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📚 Guía de Uso de Comandos",
            description=(
                "**🔤 Sintaxis de Comandos:**\n"
                "• `[]` = Parámetro opcional\n"
                "• `\"\"` = Parámetro obligatorio (texto)\n"
                "• `@usuario` = Mencionar a un usuario\n\n"
                "**💡 Ejemplos:**\n"
                "• `:xp` - Ver tu XP\n"
                "• `:xp @Juan` - Ver XP de Juan\n"
                "• `:comprar \"Poción\"` - Comprar item\n"
                "• `:transferir @María 500` - Transferir dinero\n\n"
                "**❓ ¿Necesitas ayuda?**\n"
                "Pregunta a los moderadores del servidor."
            ),
            color=0x3498db
        )
        embed.set_footer(text="💡 Tip: Usa los menús desplegables para explorar comandos específicos")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔄 Actualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def actualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🤖 Centro de Comandos",
            description=(
                "¡Bienvenido al centro de comandos! Aquí encontrarás todas las funcionalidades disponibles.\n\n"
                f"🎯 **Categorías disponibles:** {len(CATEGORIAS)}\n"
                f"⚡ **Total de comandos:** {sum(len(cat['comandos']) for cat in CATEGORIAS.values())}\n\n"
                "**Selecciona una categoría del menú desplegable para explorar:**"
            ),
            color=0x2f3136
        )
        view = CategoriaView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        # Deshabilitar todos los componentes cuando expire el timeout
        for item in self.children:
            item.disabled = True

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="comandos", aliases=["help", "ayuda", "commands"])
    async def comandos(self, ctx):
        """Comando mejorado para mostrar el menú de comandos interactivo"""
        
        embed = discord.Embed(
            title="🤖 Centro de Comandos",
            description=(
                "¡Bienvenido al centro de comandos! Aquí encontrarás todas las funcionalidades disponibles.\n\n"
                f"🎯 **Categorías disponibles:** {len(CATEGORIAS)}\n"
                f"⚡ **Total de comandos:** {sum(len(cat['comandos']) for cat in CATEGORIAS.values())}\n\n"
                "**Selecciona una categoría del menú desplegable para explorar:**"
            ),
            color=0x2f3136
        )
        
        # Agregar campo con preview de categorías
        categorias_preview = []
        for cat_name, cat_data in CATEGORIAS.items():
            categorias_preview.append(f"{cat_data['emoji']} **{cat_name.split(' ', 1)[1]}** - {len(cat_data['comandos'])} comandos")
        
        embed.add_field(
            name="📋 Vista Rápida:",
            value="\n".join(categorias_preview),
            inline=False
        )
        
        embed.set_footer(
            text=f"Solicitado por {ctx.author.display_name} • Usa los botones y menús para navegar",
            icon_url=ctx.author.display_avatar.url
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await ctx.send(embed=embed, view=CategoriaView())

async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))