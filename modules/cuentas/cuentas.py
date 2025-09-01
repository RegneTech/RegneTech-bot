import discord
from discord.ext import commands
import asyncio
import aiohttp
import os

class Cuentas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comprar_emoji = None
        self.info_emoji = None
    
    async def setup_emojis(self):
        """Crear emojis personalizados si no existen"""
        guild = self.bot.get_guild(self.bot.guilds[0].id)  # Primer servidor del bot
        
        # Buscar si ya existen los emojis
        for emoji in guild.emojis:
            if emoji.name == "comprar":
                self.comprar_emoji = emoji
            elif emoji.name == "info":
                self.info_emoji = emoji
        
        # Si no existen, crearlos
        if not self.comprar_emoji:
            try:
                # Asegúrate de que tienes estos archivos en tu proyecto de Railway
                with open('resources/emojis/comprar.png', 'rb') as f:
                    self.comprar_emoji = await guild.create_custom_emoji(
                        name='comprar',
                        image=f.read()
                    )
            except FileNotFoundError:
                print("No se encontró el archivo comprar.png, usando emoji por defecto")
                self.comprar_emoji = "🛒"
            except Exception as e:
                print(f"Error creando emoji comprar: {e}")
                self.comprar_emoji = "🛒"
        
        if not self.info_emoji:
            try:
                with open('resources/emojis/info.png', 'rb') as f:
                    self.info_emoji = await guild.create_custom_emoji(
                        name='info',
                        image=f.read()
                    )
            except FileNotFoundError:
                print("No se encontró el archivo info.png, usando emoji por defecto")
                self.info_emoji = "ℹ️"
            except Exception as e:
                print(f"Error creando emoji info: {e}")
                self.info_emoji = "ℹ️"
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que se ejecuta cuando el bot está listo"""
        print("Bot conectado, configurando emojis...")
        await self.setup_emojis()
        print("Emojis configurados, esperando 2 segundos antes de enviar embed...")
        await asyncio.sleep(2)
        await self.send_disney_embed()
    
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
                color=0x003E78  # Color personalizado #003E78
            )
            
            # Agregar el texto
            embed.add_field(
                name="",
                value="Disney ┃ Lifetime ⇨ 1€",
                inline=False
            )
            
            # Agregar imagen debajo del texto
            embed.set_image(url="attachment://Disney.png")
            
            # Crear la vista con los botones
            view = DisneyButtonView(self.comprar_emoji, self.info_emoji)
            
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
    def __init__(self, comprar_emoji=None, info_emoji=None):
        super().__init__(timeout=None)
        self.comprar_emoji = comprar_emoji or "🛒"
        self.info_emoji = info_emoji or "ℹ️"
        
        # Actualizar los botones con los emojis
        self.comprar_button.emoji = self.comprar_emoji
        self.info_button.emoji = self.info_emoji
    
    @discord.ui.button(label="Comprar", style=discord.ButtonStyle.success)
    async def comprar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Crear canal de ticket
        guild = interaction.guild
        user = interaction.user
        
        # Obtener el canal de Disney para crear el ticket debajo de él
        disney_channel = guild.get_channel(1412183751836045393)
        category = disney_channel.category if disney_channel else None
        
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
        
        # Crear el canal de ticket debajo del canal de Disney
        ticket_channel = await guild.create_text_channel(
            name=f"disney-{user.name}",
            overwrites=overwrites,
            category=category,
            position=disney_channel.position + 1 if disney_channel else None
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
    
    @discord.ui.button(label="Info", style=discord.ButtonStyle.secondary)
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mensaje solo visible para el usuario
        info_message = """La cuenta de Disney cuesta 1€ y es lifetime. Al presionar **Comprar**, aceptas nuestros Términos y Condiciones. La entrega es inmediata y el proceso es rápido y sencillo."""
        
        await interaction.response.send_message(info_message, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cuentas(bot))