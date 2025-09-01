import discord
from discord.ext import commands
import asyncio
import aiohttp
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Cuentas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comprar_emoji = "🛒"  # Emoji por defecto
        self.info_emoji = "ℹ️"     # Emoji por defecto
        self.target_guild_id = None  # ID del servidor específico
        self.disney_channel_id = 1412183751836045393
        self.staff_role_id = 1400106792280658070
        self.setup_complete = False
    
    async def setup_emojis(self):
        """Crear emojis personalizados si no existen"""
        if not self.bot.guilds:
            logger.warning("No hay servidores disponibles para crear emojis")
            return
        
        # Usar el primer servidor o uno específico
        guild = self.bot.guilds[0] if not self.target_guild_id else self.bot.get_guild(self.target_guild_id)
        
        if not guild:
            logger.error("No se pudo obtener el servidor para crear emojis")
            return
        
        try:
            # Buscar si ya existen los emojis
            existing_emojis = {emoji.name: emoji for emoji in guild.emojis}
            
            if "comprar" in existing_emojis:
                self.comprar_emoji = existing_emojis["comprar"]
                logger.info("Emoji 'comprar' encontrado")
            else:
                # Intentar crear emoji personalizado
                await self._create_custom_emoji(guild, "comprar", "resources/emojis/comprar.png")
            
            if "info" in existing_emojis:
                self.info_emoji = existing_emojis["info"]
                logger.info("Emoji 'info' encontrado")
            else:
                # Intentar crear emoji personalizado
                await self._create_custom_emoji(guild, "info", "resources/emojis/info.png")
                
        except Exception as e:
            logger.error(f"Error en setup_emojis: {e}")
    
    async def _create_custom_emoji(self, guild, name, file_path):
        """Crear un emoji personalizado"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    emoji = await guild.create_custom_emoji(name=name, image=f.read())
                    if name == "comprar":
                        self.comprar_emoji = emoji
                    elif name == "info":
                        self.info_emoji = emoji
                    logger.info(f"Emoji '{name}' creado exitosamente")
            else:
                logger.warning(f"Archivo {file_path} no encontrado, usando emoji por defecto")
        except discord.HTTPException as e:
            logger.error(f"Error HTTP creando emoji {name}: {e}")
        except Exception as e:
            logger.error(f"Error inesperado creando emoji {name}: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que se ejecuta cuando el bot está listo"""
        if self.setup_complete:
            return  # Evitar múltiples ejecuciones
        
        logger.info("Bot conectado, configurando emojis...")
        
        # Esperar un poco para asegurar que todo esté cargado
        await asyncio.sleep(3)
        
        try:
            await self.setup_emojis()
            logger.info("Emojis configurados")
            
            # Enviar embed solo si el canal existe
            channel = self.bot.get_channel(self.disney_channel_id)
            if channel:
                await self.send_disney_embed()
                logger.info("Embed de Disney enviado")
            else:
                logger.error(f"Canal con ID {self.disney_channel_id} no encontrado")
                
        except Exception as e:
            logger.error(f"Error en on_ready: {e}")
        finally:
            self.setup_complete = True
    
    @commands.command(name="send_disney")
    @commands.has_permissions(administrator=True)
    async def send_disney_manual(self, ctx):
        """Comando manual para enviar el embed de Disney"""
        try:
            await self.send_disney_embed()
            await ctx.send("✅ Embed enviado correctamente", delete_after=5)
            await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"❌ Error enviando embed: {e}", delete_after=10)
            logger.error(f"Error en send_disney_manual: {e}")
    
    @commands.command(name="setup_disney")
    @commands.has_permissions(administrator=True)
    async def setup_disney(self, ctx):
        """Comando para reconfigurar todo"""
        try:
            self.setup_complete = False
            await self.setup_emojis()
            await ctx.send("✅ Setup completado", delete_after=5)
            await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"❌ Error en setup: {e}", delete_after=10)
    
    async def send_disney_embed(self):
        """Función para enviar el embed de Disney"""
        channel = self.bot.get_channel(self.disney_channel_id)
        
        if not channel:
            logger.error(f"Canal {self.disney_channel_id} no encontrado")
            return
        
        try:
            # Crear el embed
            embed = discord.Embed(
                title="🏰 Disney Streaming Account",
                description="",
                color=0x003E78
            )
            
            # Agregar el campo principal
            embed.add_field(
                name="💫 Oferta Especial",
                value="**Disney+ ⚡ Lifetime ⇨ 1€**\n\n✨ Acceso completo y permanente\n🚀 Entrega inmediata\n🔒 Garantía incluida",
                inline=False
            )
            
            # Footer con información adicional
            embed.set_footer(text="🎯 Haz clic en los botones para más información")
            
            # Crear la vista con los botones
            view = DisneyButtonView(self.comprar_emoji, self.info_emoji)
            
            # Intentar enviar con imagen
            image_path = "resources/images/Disney.png"
            if os.path.exists(image_path):
                embed.set_image(url="attachment://Disney.png")
                file = discord.File(image_path, filename="Disney.png")
                message = await channel.send(file=file, embed=embed, view=view)
            else:
                logger.warning("Imagen Disney.png no encontrada, enviando sin imagen")
                message = await channel.send(embed=embed, view=view)
            
            # Hacer que la vista sea persistente
            self.bot.add_view(view, message_id=message.id)
            logger.info("Embed de Disney enviado exitosamente")
            
        except discord.HTTPException as e:
            logger.error(f"Error HTTP enviando embed: {e}")
        except Exception as e:
            logger.error(f"Error inesperado enviando embed: {e}")

class DisneyButtonView(discord.ui.View):
    def __init__(self, comprar_emoji=None, info_emoji=None):
        super().__init__(timeout=None)  # Hacer la vista persistente
        self.comprar_emoji = comprar_emoji or "🛒"
        self.info_emoji = info_emoji or "ℹ️"
    
    @discord.ui.button(label="Comprar", style=discord.ButtonStyle.success, emoji="🛒")
    async def comprar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Verificar si ya tiene un ticket abierto
            existing_ticket = discord.utils.get(
                interaction.guild.channels, 
                name=f"disney-{interaction.user.name.lower()}"
            )
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {existing_ticket.mention}", 
                    ephemeral=True
                )
                return
            
            # Crear canal de ticket
            guild = interaction.guild
            user = interaction.user
            
            # Obtener el canal de Disney para crear el ticket debajo de él
            disney_channel = guild.get_channel(1412183751836045393)
            category = disney_channel.category if disney_channel else None
            
            # Configurar permisos para el ticket
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True
                )
            }
            
            # Agregar permisos para el rol específico
            staff_role = guild.get_role(1400106792280658070)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True,
                    manage_messages=True
                )
            
            # Crear el canal de ticket
            ticket_channel = await guild.create_text_channel(
                name=f"disney-{user.name.lower()}",
                overwrites=overwrites,
                category=category,
                topic=f"Ticket de Disney+ para {user.display_name}",
                position=disney_channel.position + 1 if disney_channel else None
            )
            
            # Crear embed para el ticket
            ticket_embed = discord.Embed(
                title="🎫 Nuevo Ticket - Disney+",
                description=f"**Usuario:** {user.mention}\n**Producto:** Disney+ Lifetime\n**Precio:** 1€",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            ticket_embed.add_field(
                name="📋 Información",
                value="Un miembro del staff te atenderá pronto.\nPor favor, mantén la paciencia y proporciona cualquier información adicional que te soliciten.",
                inline=False
            )
            ticket_embed.set_footer(text=f"Ticket ID: {ticket_channel.id}")
            
            # Mensaje inicial en el ticket
            staff_mention = f"<@&{1400106792280658070}>" if staff_role else ""
            initial_message = f"¡Hola {user.mention}! 👋\n{staff_mention}"
            
            await ticket_channel.send(initial_message, embed=ticket_embed)
            
            # Respuesta al usuario
            await interaction.response.send_message(
                f"✅ ¡Ticket creado exitosamente! {ticket_channel.mention}\nUn miembro del staff te atenderá pronto.", 
                ephemeral=True
            )
            
            logger.info(f"Ticket creado para {user.name} (ID: {user.id})")
            
        except discord.HTTPException as e:
            await interaction.response.send_message(
                "❌ Error creando el ticket. Contacta con un administrador.", 
                ephemeral=True
            )
            logger.error(f"Error HTTP creando ticket: {e}")
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error inesperado. Contacta con un administrador.", 
                    ephemeral=True
                )
            logger.error(f"Error inesperado creando ticket: {e}")
    
    @discord.ui.button(label="Información", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Crear embed informativo
            info_embed = discord.Embed(
                title="📋 Información - Disney+ Lifetime",
                color=0x0099ff
            )
            
            info_embed.add_field(
                name="💰 Precio",
                value="**1€** - Pago único",
                inline=True
            )
            
            info_embed.add_field(
                name="⏱️ Duración",
                value="**Lifetime** - Para siempre",
                inline=True
            )
            
            info_embed.add_field(
                name="🚀 Entrega",
                value="**Inmediata** - Al instante",
                inline=True
            )
            
            info_embed.add_field(
                name="📱 Características",
                value="• Acceso completo a Disney+\n• Todas las películas y series\n• Calidad HD/4K\n• Múltiples dispositivos",
                inline=False
            )
            
            info_embed.add_field(
                name="⚠️ Términos",
                value="Al comprar aceptas nuestros Términos y Condiciones. La cuenta es personal e intransferible.",
                inline=False
            )
            
            info_embed.set_footer(text="¿Listo para comprar? ¡Haz clic en el botón verde!")
            
            await interaction.response.send_message(embed=info_embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ Error mostrando información. Intenta nuevamente.", 
                ephemeral=True
            )
            logger.error(f"Error mostrando info: {e}")

async def setup(bot: commands.Bot):
    """Función setup para cargar el cog"""
    try:
        await bot.add_cog(Cuentas(bot))
        logger.info("Cog 'Cuentas' cargado exitosamente")
    except Exception as e:
        logger.error(f"Error cargando cog 'Cuentas': {e}")
        raise