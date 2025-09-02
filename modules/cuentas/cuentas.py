import discord
from discord.ext import commands
import asyncio
import os
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class Cuentas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comprar_emoji = "🛒"  # Fallback por defecto
        self.info_emoji = "ℹ️"     # Fallback por defecto
        self.disney_channel_id = 1412183751836045393
        self.staff_role_id = 1400106792280658070
        self.setup_complete = False
        self.embed_sent = False  # Para evitar envío múltiple
    
    async def find_emojis(self):
        """Buscar los emojis personalizados en el servidor"""
        if not self.bot.guilds:
            logger.warning("No hay servidores disponibles para buscar emojis")
            return
        
        # Buscar en todos los servidores del bot
        for guild in self.bot.guilds:
            for emoji in guild.emojis:
                if emoji.name == "comprar":
                    self.comprar_emoji = emoji
                    logger.info(f"✅ Emoji 'comprar' encontrado: {emoji}")
                elif emoji.name == "info":
                    self.info_emoji = emoji
                    logger.info(f"✅ Emoji 'info' encontrado: {emoji}")
        
        # Si no los encuentra, mantener los fallback
        if isinstance(self.comprar_emoji, str):
            logger.warning("⚠️ Emoji personalizado 'comprar' no encontrado, usando 🛒")
        if isinstance(self.info_emoji, str):
            logger.warning("⚠️ Emoji personalizado 'info' no encontrado, usando ℹ️")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que se ejecuta cuando el bot está listo"""
        if self.setup_complete:
            return  # Evitar múltiples ejecuciones
        
        logger.info("🔧 Configurando módulo de cuentas...")
        
        # Esperar un poco para asegurar que todo esté cargado
        await asyncio.sleep(2)
        
        try:
            # Buscar emojis personalizados
            await self.find_emojis()
            logger.info("✅ Emojis configurados")
            
            # Enviar embed solo una vez
            if not self.embed_sent:
                channel = self.bot.get_channel(self.disney_channel_id)
                if channel:
                    await self.send_disney_embed()
                    self.embed_sent = True
                    logger.info("✅ Embed de Disney enviado")
                else:
                    logger.error(f"❌ Canal con ID {self.disney_channel_id} no encontrado")
                
        except Exception as e:
            logger.error(f"❌ Error en on_ready del módulo cuentas: {e}")
        finally:
            self.setup_complete = True
    
    @commands.command(name="send_disney")
    @commands.has_permissions(administrator=True)
    async def send_disney_manual(self, ctx):
        """Comando manual para enviar el embed de Disney"""
        try:
            await self.find_emojis()  # Actualizar emojis
            await self.send_disney_embed()
            
            embed = discord.Embed(
                title="✅ Embed enviado",
                description="El embed de Disney se envió correctamente",
                color=0x00ff00
            )
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error enviando embed: {e}",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            logger.error(f"❌ Error en send_disney_manual: {e}")
    
    @commands.command(name="refresh_emojis")
    @commands.has_permissions(administrator=True)
    async def refresh_emojis(self, ctx):
        """Comando para actualizar los emojis"""
        try:
            await self.find_emojis()
            embed = discord.Embed(
                title="✅ Emojis actualizados",
                description=f"Comprar: {self.comprar_emoji}\nInfo: {self.info_emoji}",
                color=0x00ff00
            )
            await ctx.send(embed=embed, delete_after=10)
            await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"❌ Error actualizando emojis: {e}", delete_after=10)
    
    async def send_disney_embed(self):
        """Función para enviar el embed de Disney"""
        channel = self.bot.get_channel(self.disney_channel_id)
        
        if not channel:
            logger.error(f"❌ Canal {self.disney_channel_id} no encontrado")
            return
        
        try:
            # Crear el embed
            embed = discord.Embed(
                title="**Disney Plus Lifetime ⇨ 1€**",
                description="",
                color=0x003E78
            )
            
            # Timestamp
            embed.timestamp = discord.utils.utcnow()
            
            # Crear la vista con los botones (usando emojis encontrados)
            view = DisneyButtonView(
                comprar_emoji=self.comprar_emoji,
                info_emoji=self.info_emoji,
                disney_channel_id=self.disney_channel_id,
                staff_role_id=self.staff_role_id
            )
            
            # Intentar enviar con imagen si existe
            image_path = "resources/images/Disney.png"
            if os.path.exists(image_path):
                embed.set_image(url="attachment://Disney.png")
                file = discord.File(image_path, filename="Disney.png")
                message = await channel.send(file=file, embed=embed, view=view)
            else:
                logger.info("ℹ️ Imagen Disney.png no encontrada, enviando sin imagen")
                message = await channel.send(embed=embed, view=view)
            
            # Hacer que la vista sea persistente
            self.bot.add_view(view, message_id=message.id)
            logger.info(f"✅ Embed de Disney enviado exitosamente (ID: {message.id})")
            
        except discord.HTTPException as e:
            logger.error(f"❌ Error HTTP enviando embed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado enviando embed: {e}")
            raise

class DisneyButtonView(discord.ui.View):
    def __init__(self, comprar_emoji=None, info_emoji=None, disney_channel_id=None, staff_role_id=None):
        super().__init__(timeout=None)  # Vista persistente
        self.comprar_emoji = comprar_emoji or "🛒"
        self.info_emoji = info_emoji or "ℹ️"
        self.disney_channel_id = disney_channel_id
        self.staff_role_id = staff_role_id
        
        # Actualizar los emojis en los botones
        self.update_button_emojis()
    
    def update_button_emojis(self):
        """Actualizar los emojis de los botones"""
        # Encontrar y actualizar los botones
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "disney_comprar":
                    item.emoji = self.comprar_emoji
                elif item.custom_id == "disney_info":
                    item.emoji = self.info_emoji
    
    @discord.ui.button(
        label="Comprar", 
        style=discord.ButtonStyle.secondary, 
        custom_id="disney_comprar",
        emoji="🛒"
    )
    async def comprar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Defer la respuesta para tener más tiempo
            await interaction.response.defer(ephemeral=True)
            
            user = interaction.user
            guild = interaction.guild
            
            # Verificar si ya tiene un ticket abierto
            ticket_name = f"disney-{user.name.lower().replace(' ', '-')}"
            existing_ticket = discord.utils.get(guild.channels, name=ticket_name)
            
            if existing_ticket:
                await interaction.followup.send(
                    f"❌ Ya tienes un ticket abierto: {existing_ticket.mention}",
                    ephemeral=True
                )
                return
            
            # Obtener el canal de Disney para crear el ticket debajo
            disney_channel = guild.get_channel(self.disney_channel_id)
            category = disney_channel.category if disney_channel else None
            
            # Configurar permisos del ticket
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True
                )
            }
            
            # Agregar permisos para el rol de staff
            staff_role = guild.get_role(self.staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True
                )
            
            # Crear el canal del ticket
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                category=category,
                topic=f"Ticket de Disney+ para {user.display_name} | ID: {user.id}",
                position=disney_channel.position + 1 if disney_channel else None
            )
            
            # Crear embed para el mensaje inicial del ticket
            ticket_embed = discord.Embed(
                title="🎫 Nuevo Ticket - Disney+ Lifetime",
                color=0x003E78,
                timestamp=discord.utils.utcnow()
            )
            
            ticket_embed.add_field(
                name="👤 Cliente",
                value=f"{user.mention}\n`{user.display_name}`\n`ID: {user.id}`",
                inline=True
            )
            
            ticket_embed.add_field(
                name="🎬 Producto",
                value="**Disney+ Lifetime**\n💰 Precio: **1€**\n⚡ Entrega: Inmediata",
                inline=True
            )
            
            ticket_embed.add_field(
                name="📋 Estado",
                value="🟡 **Pendiente**\nEsperando atención del staff",
                inline=False
            )
            
            ticket_embed.add_field(
                name="ℹ️ Instrucciones",
                value="• Un miembro del staff te atenderá pronto\n" +
                      "• Mantén la paciencia y sé respetuoso\n" +
                      "• Proporciona cualquier información solicitada\n" +
                      "• El proceso es rápido y seguro",
                inline=False
            )
            
            ticket_embed.set_footer(
                text=f"Ticket ID: {ticket_channel.id} | Creado",
                icon_url=user.avatar.url if user.avatar else user.default_avatar.url
            )
            
            ticket_embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
            # Mensaje de bienvenida
            welcome_message = f"¡Hola {user.mention}! 👋 Bienvenido a tu ticket de Disney+.\n"
            if staff_role:
                welcome_message += f"{staff_role.mention} Un cliente está esperando atención."
            
            # Enviar mensaje inicial
            await ticket_channel.send(welcome_message, embed=ticket_embed)
            
            # Respuesta exitosa al usuario
            success_embed = discord.Embed(
                title="✅ Ticket creado exitosamente",
                description=f"Tu ticket ha sido creado: {ticket_channel.mention}\n\n" +
                           "📞 **¿Qué sigue?**\n" +
                           "• Un miembro del staff te contactará pronto\n" +
                           "• El proceso de compra es rápido y seguro\n" +
                           "• Recibirás tu cuenta inmediatamente después del pago",
                color=0x00ff00
            )
            success_embed.set_footer(text="¡Gracias por elegirnos!")
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            logger.info(f"✅ Ticket creado para {user.name} (ID: {user.id}) - Canal: {ticket_channel.name}")
            
        except discord.HTTPException as e:
            logger.error(f"❌ Error HTTP creando ticket: {e}")
            try:
                await interaction.followup.send(
                    "❌ Error creando el ticket debido a permisos insuficientes. Contacta con un administrador.",
                    ephemeral=True
                )
            except:
                pass
        except Exception as e:
            logger.error(f"❌ Error inesperado creando ticket: {e}")
            try:
                await interaction.followup.send(
                    "❌ Error inesperado. Por favor, contacta con un administrador.",
                    ephemeral=True
                )
            except:
                pass
    
    @discord.ui.button(
        label="Información", 
        style=discord.ButtonStyle.secondary, 
        custom_id="disney_info",
        emoji="ℹ️"
    )
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Crear embed informativo detallado
            info_embed = discord.Embed(
                title="📋 Disney+ Lifetime - Información Completa",
                description="Toda la información que necesitas saber sobre nuestro servicio",
                color=0x003E78
            )
            
            # Información de precio
            info_embed.add_field(
                name="💰 Precio y Pago",
                value="**1€** - Pago único\n" +
                      "💳 Métodos: PayPal, Stripe, Crypto\n" +
                      "🔒 Transacciones 100% seguras",
                inline=True
            )
            
            # Información de duración
            info_embed.add_field(
                name="⏰ Duración",
                value="**Lifetime** - Para siempre\n" +
                      "♾️ Sin renovaciones\n" +
                      "🎯 Una sola compra",
                inline=True
            )
            
            # Información de entrega
            info_embed.add_field(
                name="🚀 Entrega",
                value="**Instantánea** - Al momento\n" +
                      "📧 Datos por mensaje privado\n" +
                      "⚡ Acceso inmediato",
                inline=True
            )
            
            # Características del servicio
            info_embed.add_field(
                name="🎬 Características Incluidas",
                value="• ✅ Acceso completo a Disney+\n" +
                      "• 🎭 Todas las películas y series\n" +
                      "• 🎨 Contenido original exclusivo\n" +
                      "• 📱 Compatible con todos los dispositivos\n" +
                      "• 🌍 Funciona en cualquier región\n" +
                      "• 🔊 Audio y subtítulos en varios idiomas",
                inline=False
            )
            
            # Calidad y soporte
            info_embed.add_field(
                name="⭐ Calidad Premium",
                value="• 🎥 Resolución hasta 4K UHD\n" +
                      "• 🔊 Audio Dolby Atmos\n" +
                      "• 📺 Streaming sin interrupciones\n" +
                      "• 💾 Descargas para ver offline",
                inline=True
            )
            
            # Soporte y garantías
            info_embed.add_field(
                name="🛡️ Garantías y Soporte",
                value="• 🔧 Soporte técnico incluido\n" +
                      "• 🔄 Reemplazos gratuitos si es necesario\n" +
                      "• 👥 Atención personalizada\n" +
                      "• ⏱️ Respuesta en menos de 24h",
                inline=True
            )
            
            # Términos importantes
            info_embed.add_field(
                name="⚠️ Términos y Condiciones",
                value="• 📝 Al comprar aceptas nuestros T&C\n" +
                      "• 👤 Cuenta personal e intransferible\n" +
                      "• 🔐 Cambio de credenciales prohibido\n" +
                      "• 🤝 Uso responsable requerido\n" +
                      "• 💼 Solo para uso personal",
                inline=False
            )
            
            # Proceso de compra
            info_embed.add_field(
                name="🛒 ¿Cómo Comprar?",
                value="1️⃣ Haz clic en **'Comprar'**\n" +
                      "2️⃣ Se abrirá un ticket privado\n" +
                      "3️⃣ El staff te contactará\n" +
                      "4️⃣ Realizas el pago\n" +
                      "5️⃣ Recibes tu cuenta al instante",
                inline=True
            )
            
            # FAQ rápido
            info_embed.add_field(
                name="❓ Preguntas Frecuentes",
                value="**¿Es legal?** ✅ Totalmente legal\n" +
                      "**¿Funciona en mi país?** 🌍 Sí, mundial\n" +
                      "**¿Cuánto dura?** ♾️ Para siempre\n" +
                      "**¿Hay soporte?** 💬 Sí, 24/7\n" +
                      "**¿Es seguro?** 🔒 100% seguro",
                inline=True
            )
            
            info_embed.set_footer(
                text="¿Listo para disfrutar Disney+ para siempre? ¡Haz clic en Comprar! 🎬",
                icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
            )
            
            info_embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/disney/disney-original.svg")
            
            await interaction.response.send_message(embed=info_embed, ephemeral=True)
            
            logger.info(f"ℹ️ Info mostrada a {interaction.user.name} (ID: {interaction.user.id})")
            
        except Exception as e:
            logger.error(f"❌ Error mostrando información: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Error mostrando información. Por favor, intenta nuevamente o contacta con el staff.",
                    ephemeral=True
                )
            except:
                pass

async def setup(bot: commands.Bot):
    """Función setup para cargar el cog"""
    try:
        await bot.add_cog(Cuentas(bot))
        logger.info("✅ Cog 'Cuentas' cargado exitosamente")
    except Exception as e:
        logger.error(f"❌ Error cargando cog 'Cuentas': {e}")
        raise