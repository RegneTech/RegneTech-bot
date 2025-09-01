import discord
from discord.ext import commands

class Cuentas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_sent = False  # Para evitar enviar múltiples veces
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que se ejecuta cuando el bot está listo"""
        if not self.embed_sent:
            await self.send_disney_embed()
            self.embed_sent = True
    
    @commands.command(name="send_disney")
    @commands.has_permissions(administrator=True)
    async def send_disney_manual(self, ctx):
        """Comando manual para enviar el embed de Disney"""
        await self.send_disney_embed()
        await ctx.message.delete()  # Borra el comando
    
    async def send_disney_embed(self):
        """Función para enviar el embed de Disney"""
        channel_id = 1412183751836045393
        channel = self.bot.get_channel(channel_id)
        
        if channel:
            # Crear el embed
            embed = discord.Embed(
                title="Disney Streaming Account",
                color=0x1e3a8a  # Azul marino
            )
            
            # Agregar imagen al embed
            embed.set_image(url="attachment://Disney.png")
            
            # Agregar el texto debajo de la imagen
            embed.add_field(
                name="",
                value="Disney ┃ Lifetime ⇨ 1€",
                inline=False
            )
            
            # Crear la vista con los botones
            view = DisneyButtonView()
            
            # Enviar con archivo adjunto
            try:
                file = discord.File("resources/images/Disney.png", filename="Disney.png")
                await channel.send(file=file, embed=embed, view=view)
            except FileNotFoundError:
                # Si no encuentra el archivo, envía sin imagen
                embed.set_image(url="")
                await channel.send(embed=embed, view=view)
            except Exception as e:
                print(f"Error enviando embed: {e}")

class DisneyButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Sin timeout para que los botones persistan
    
    @discord.ui.button(label="Comprar", style=discord.ButtonStyle.primary, emoji="💰")
    async def comprar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Crear canal de ticket
        guild = interaction.guild
        user = interaction.user
        
        # Configurar permisos para el ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Agregar permisos para el rol específico
        role = guild.get_role(1400106792280658070)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Crear el canal de ticket
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites
        )
        
        # Mensaje en el ticket
        mention_role = f"<@&{1400106792280658070}>"
        mention_user = user.mention
        
        ticket_message = f"{mention_role} {mention_user} está interesado en comprar una cuenta de Disney."
        
        await ticket_channel.send(ticket_message)
        
        # Respuesta al usuario
        await interaction.response.send_message(
            f"✅ Se ha creado tu ticket: {ticket_channel.mention}", 
            ephemeral=True
        )
    
    @discord.ui.button(label="Info", style=discord.ButtonStyle.primary, emoji="ℹ️")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mensaje solo visible para el usuario
        info_message = """La cuenta de Disney cuesta 1€ y es lifetime. Al presionar **Comprar**, aceptas nuestros Términos y Condiciones. La entrega es inmediata y el proceso es rápido y sencillo."""
        
        await interaction.response.send_message(info_message, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cuentas(bot))