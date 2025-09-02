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
        self.staff_role_id = 1400106792280658070
        self.setup_complete = False
        
        # Configuración de todos los servicios
        self.servicios = {
            'disney': {
                'channel_id': 1412183751836045393,
                'precio': 1,
                'color': 0x003E78,
                'nombre': 'Disney Plus',
                'emoji': '🎬',
                'imagen': 'Disney.png'
            },
            'spotify': {
                'channel_id': 1412492877291851796,
                'precio': 1,
                'color': 0x1DB954,
                'nombre': 'Spotify',
                'emoji': '🎵',
                'imagen': 'Spotify.png'
            },
            'netflix': {
                'channel_id': 1412493281610305628,
                'precio': 1,
                'color': 0xE50914,
                'nombre': 'Netflix',
                'emoji': '📺',
                'imagen': 'Netflix.png'
            },
            'crunchyroll': {
                'channel_id': 1412493355287576596,
                'precio': 1,
                'color': 0xFF6600,
                'nombre': 'Crunchyroll',
                'emoji': '🍜',
                'imagen': 'Crunchyroll.png'
            },
            'youtube': {
                'channel_id': 1412493434945540147,
                'precio': 3,
                'color': 0xFF0000,
                'nombre': 'YouTube Premium',
                'emoji': '▶️',
                'imagen': 'YouTube.png'
            },
            'hbomax': {
                'channel_id': 1412493526637477890,
                'precio': 1,
                'color': 0x673AB7,
                'nombre': 'HBO Max',
                'emoji': '🎭',
                'imagen': 'HBOMax.png'
            }
        }
        
        # Control de envíos para evitar duplicados
        self.embeds_enviados = {servicio: False for servicio in self.servicios}
    
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
    
    async def cog_load(self):
        """Configuración automática al cargar el cog (similar a beginning.py)"""
        logger.info("🔧 Configurando módulo de cuentas automáticamente...")
        
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)  # Delay para estabilidad
        
        try:
            # Buscar emojis personalizados
            await self.find_emojis()
            logger.info("✅ Emojis configurados")
            
            # Configurar todos los servicios
            await self.setup_all_services()
            logger.info("✅ Todos los servicios configurados automáticamente")
            
        except Exception as e:
            logger.error(f"❌ Error en cog_load del módulo cuentas: {e}")
        finally:
            self.setup_complete = True
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Backup para configuración automática"""
        if not hasattr(self, '_auto_setup_done'):
            self._auto_setup_done = True
            await asyncio.sleep(5)  # Delay más largo para backup
            
            try:
                if not self.setup_complete:
                    await self.find_emojis()
                    await self.setup_all_services()
                    logger.info("✅ Servicios configurados (on_ready backup)")
            except Exception as e:
                logger.error(f"❌ Error en on_ready backup: {e}")
    
    async def setup_all_services(self):
        """Configura todos los servicios automáticamente"""
        for servicio_key, config in self.servicios.items():
            try:
                if not self.embeds_enviados[servicio_key]:
                    channel = self.bot.get_channel(config['channel_id'])
                    if channel:
                        await self.send_service_embed(servicio_key, config)
                        self.embeds_enviados[servicio_key] = True
                        logger.info(f"✅ Embed de {config['nombre']} enviado")
                        await asyncio.sleep(1)  # Delay entre envíos
                    else:
                        logger.error(f"❌ Canal {config['channel_id']} para {config['nombre']} no encontrado")
            except Exception as e:
                logger.error(f"❌ Error configurando {config['nombre']}: {e}")
    
    async def send_service_embed(self, servicio_key, config):
        """Función para enviar el embed de un servicio específico"""
        channel = self.bot.get_channel(config['channel_id'])
        
        if not channel:
            logger.error(f"❌ Canal {config['channel_id']} no encontrado para {config['nombre']}")
            return
        
        try:
            # Limpiar canal primero
            try:
                await channel.purge(limit=100)
                logger.info(f"🧹 Canal {config['nombre']} limpiado")
            except discord.Forbidden:
                logger.warning(f"⚠️ Sin permisos para limpiar canal {config['nombre']}")
            except Exception as e:
                logger.warning(f"⚠️ Error limpiando canal {config['nombre']}: {e}")
            
            # Crear el embed
            embed = discord.Embed(
                title=f"**{config['nombre']} Lifetime ⇨ {config['precio']}€**",
                description="",
                color=config['color']
            )
            
            # Crear la vista con los botones
            view = ServiceButtonView(
                servicio_key=servicio_key,
                config=config,
                comprar_emoji=self.comprar_emoji,
                info_emoji=self.info_emoji,
                staff_role_id=self.staff_role_id
            )
            
            # Intentar enviar con imagen si existe
            image_path = f"resources/images/{config['imagen']}"
            if os.path.exists(image_path):
                embed.set_image(url=f"attachment://{config['imagen']}")
                file = discord.File(image_path, filename=config['imagen'])
                message = await channel.send(file=file, embed=embed, view=view)
            else:
                logger.info(f"ℹ️ Imagen {config['imagen']} no encontrada, enviando sin imagen")
                message = await channel.send(embed=embed, view=view)
            
            # Hacer que la vista sea persistente
            self.bot.add_view(view, message_id=message.id)
            logger.info(f"✅ Embed de {config['nombre']} enviado exitosamente (ID: {message.id})")
            
        except discord.HTTPException as e:
            logger.error(f"❌ Error HTTP enviando embed de {config['nombre']}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado enviando embed de {config['nombre']}: {e}")
            raise
    
    @commands.command(name="setup_services")
    @commands.has_permissions(administrator=True)
    async def setup_services_manual(self, ctx):
        """Comando manual para configurar todos los servicios"""
        loading_msg = await ctx.send("🔧 Configurando todos los servicios...")
        
        try:
            await self.find_emojis()  # Actualizar emojis
            
            success_count = 0
            error_count = 0
            
            for servicio_key, config in self.servicios.items():
                try:
                    await self.send_service_embed(servicio_key, config)
                    self.embeds_enviados[servicio_key] = True
                    success_count += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Error configurando {config['nombre']}: {e}")
                    error_count += 1
            
            embed = discord.Embed(
                title="📊 Configuración Completada",
                color=0x00ff00 if error_count == 0 else 0xffaa00
            )
            
            embed.add_field(
                name="✅ Exitosos",
                value=str(success_count),
                inline=True
            )
            
            embed.add_field(
                name="❌ Errores", 
                value=str(error_count),
                inline=True
            )
            
            embed.add_field(
                name="📊 Total",
                value=f"{success_count + error_count} servicios",
                inline=True
            )
            
            await loading_msg.edit(content="", embed=embed)
            await ctx.message.delete()
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error configurando servicios: {e}",
                color=0xff0000
            )
            await loading_msg.edit(content="", embed=embed)
            logger.error(f"❌ Error en setup_services_manual: {e}")
    
    @commands.command(name="setup_single")
    @commands.has_permissions(administrator=True)
    async def setup_single_service(self, ctx, servicio: str = None):
        """Comando para configurar un servicio específico"""
        if not servicio or servicio not in self.servicios:
            servicios_disponibles = ", ".join(self.servicios.keys())
            await ctx.send(f"❌ Servicio no válido. Disponibles: {servicios_disponibles}")
            return
        
        try:
            await self.find_emojis()
            config = self.servicios[servicio]
            await self.send_service_embed(servicio, config)
            self.embeds_enviados[servicio] = True
            
            embed = discord.Embed(
                title="✅ Servicio configurado",
                description=f"El embed de **{config['nombre']}** se envió correctamente",
                color=0x00ff00
            )
            await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete()
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error configurando {servicio}: {e}",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
            logger.error(f"❌ Error en setup_single_service: {e}")
    
    @commands.command(name="services_status")
    @commands.has_permissions(administrator=True)
    async def services_status(self, ctx):
        """Muestra el estado de todos los servicios"""
        embed = discord.Embed(
            title="📊 Estado de Servicios",
            color=0x00ffff
        )
        
        for servicio_key, config in self.servicios.items():
            channel = self.bot.get_channel(config['channel_id'])
            status = "✅ Configurado" if self.embeds_enviados[servicio_key] else "❌ No configurado"
            channel_status = "✅ Encontrado" if channel else "❌ No encontrado"
            
            embed.add_field(
                name=f"{config['emoji']} {config['nombre']}",
                value=f"**Estado:** {status}\n**Canal:** {channel_status}\n**Precio:** {config['precio']}€",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
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

class ServiceButtonView(discord.ui.View):
    def __init__(self, servicio_key, config, comprar_emoji=None, info_emoji=None, staff_role_id=None):
        super().__init__(timeout=None)  # Vista persistente
        self.servicio_key = servicio_key
        self.config = config
        self.comprar_emoji = comprar_emoji or "🛒"
        self.info_emoji = info_emoji or "ℹ️"
        self.staff_role_id = staff_role_id
        
        # Crear los botones con los emojis correctos desde el inicio
        self.clear_items()  # Limpiar botones por defecto
        self.add_buttons_with_custom_emojis()
    
    def add_buttons_with_custom_emojis(self):
        """Crear los botones con los emojis personalizados"""
        # Botón de comprar
        comprar_btn = discord.ui.Button(
            label="Comprar",
            style=discord.ButtonStyle.secondary,
            custom_id=f"{self.servicio_key}_comprar",
            emoji=self.comprar_emoji
        )
        comprar_btn.callback = self.comprar_button_callback
        
        # Botón de información
        info_btn = discord.ui.Button(
            label="Información",
            style=discord.ButtonStyle.secondary,
            custom_id=f"{self.servicio_key}_info",
            emoji=self.info_emoji
        )
        info_btn.callback = self.info_button_callback
        
        # Añadir los botones a la vista
        self.add_item(comprar_btn)
        self.add_item(info_btn)
    
    async def comprar_button_callback(self, interaction: discord.Interaction):
        """Callback para el botón de comprar"""
        try:
            # Defer la respuesta para tener más tiempo
            await interaction.response.defer(ephemeral=True)
            
            user = interaction.user
            guild = interaction.guild
            
            # Verificar si ya tiene un ticket abierto para este servicio
            ticket_name = f"{self.servicio_key}-{user.name.lower().replace(' ', '-')}"
            existing_ticket = discord.utils.get(guild.channels, name=ticket_name)
            
            if existing_ticket:
                await interaction.followup.send(
                    f"❌ Ya tienes un ticket abierto para {self.config['nombre']}: {existing_ticket.mention}",
                    ephemeral=True
                )
                return
            
            # Obtener el canal del servicio para crear el ticket debajo
            service_channel = guild.get_channel(self.config['channel_id'])
            category = service_channel.category if service_channel else None
            
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
                topic=f"Ticket de {self.config['nombre']} para {user.display_name} | ID: {user.id}",
                position=service_channel.position + 1 if service_channel else None
            )
            
            # Crear embed para el mensaje inicial del ticket
            ticket_embed = discord.Embed(
                title=f"🎫 Nuevo Ticket - {self.config['nombre']} Lifetime",
                color=self.config['color'],
                timestamp=discord.utils.utcnow()
            )
            
            ticket_embed.add_field(
                name="👤 Cliente",
                value=f"{user.mention}\n`{user.display_name}`\n`ID: {user.id}`",
                inline=True
            )
            
            ticket_embed.add_field(
                name=f"{self.config['emoji']} Producto",
                value=f"**{self.config['nombre']} Lifetime**\n💰 Precio: **{self.config['precio']}€**\n⚡ Entrega: Inmediata",
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
            welcome_message = f"¡Hola {user.mention}! 👋 Bienvenido a tu ticket de {self.config['nombre']}.\n"
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
            
            logger.info(f"✅ Ticket de {self.config['nombre']} creado para {user.name} (ID: {user.id}) - Canal: {ticket_channel.name}")
            
        except discord.HTTPException as e:
            logger.error(f"❌ Error HTTP creando ticket de {self.config['nombre']}: {e}")
            try:
                await interaction.followup.send(
                    "❌ Error creando el ticket debido a permisos insuficientes. Contacta con un administrador.",
                    ephemeral=True
                )
            except:
                pass
        except Exception as e:
            logger.error(f"❌ Error inesperado creando ticket de {self.config['nombre']}: {e}")
            try:
                await interaction.followup.send(
                    "❌ Error inesperado. Por favor, contacta con un administrador.",
                    ephemeral=True
                )
            except:
                pass
    
    async def info_button_callback(self, interaction: discord.Interaction):
        """Callback para el botón de información"""
        try:
            # Crear embed informativo detallado
            info_embed = discord.Embed(
                title=f"{self.config['nombre']} Lifetime - Información",
                description=(
                    f"El producto que ofrecemos es **lifetime**, lo que significa que solo se paga una vez y será tuyo para siempre. "
                    f"Su precio es de **{self.config['precio']} euro{'s' if self.config['precio'] > 1 else ''}**. Al momento de realizar la compra, se abrirá automáticamente un ticket para que el **Owner** "
                    f"pueda atenderte de manera personalizada y entregarte tu cuenta lo antes posible. Ten en cuenta que al efectuar la compra "
                    f"estás aceptando nuestros **Términos y Condiciones**."
                ),
                color=self.config['color']
            )
            
            await interaction.response.send_message(embed=info_embed, ephemeral=True)
            
            logger.info(f"ℹ️ Info de {self.config['nombre']} mostrada a {interaction.user.name} (ID: {interaction.user.id})")
            
        except Exception as e:
            logger.error(f"❌ Error mostrando información de {self.config['nombre']}: {e}")
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