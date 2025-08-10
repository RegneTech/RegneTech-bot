import discord
from discord.ext import commands
import sqlite3
import datetime
import os
import asyncio
import json

# IDs de configuración
ADMIN_IDS = [1400106792196898889]
OWNER_IDS = [1400106792280658070]  # IDs de usuarios owner
OWNER_ROLE_ID = 1400106792280658070  # ID del rol de owner
LOG_CHANNEL_ID = 1400106793811705864
TICKET_PANEL_CHANNEL_ID = 1400106792821981248  # Canal donde se enviará el panel
STAFF_CHANNEL_ID = 1400106793811705861  # Canal de staff donde se ejecutan los comandos

class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Compras",
                description="Realizar compras o consultar productos",
                emoji="💰",
                value="compras"
            ),
            discord.SelectOption(
                label="Ayuda",
                description="Obtener ayuda o soporte técnico",
                emoji="❓",
                value="ayuda"
            ),
            discord.SelectOption(
                label="Reportes",
                description="Reportar problemas o bugs",
                emoji="🚨",
                value="reportes"
            ),
            discord.SelectOption(
                label="Sugerencias",
                description="Enviar sugerencias o ideas",
                emoji="💡",
                value="sugerencias"
            ),
            discord.SelectOption(
                label="Personalizado",
                description="Otro tipo de consulta",
                emoji="🎯",
                value="personalizado"
            )
        ]
        super().__init__(placeholder="🎫 Selecciona el tipo de ticket que necesitas...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        user = interaction.user
        guild = interaction.guild
        
        # Verificar si el usuario ya tiene tickets abiertos (límite de 3)
        tickets_cog = interaction.client.get_cog('Tickets')
        if tickets_cog:
            open_tickets = tickets_cog.get_user_open_tickets(user.id)
            if len(open_tickets) >= 3:
                await interaction.response.send_message(
                    f"❌ **Límite de tickets alcanzado**\n"
                    f"Ya tienes **{len(open_tickets)}** tickets abiertos. Cierra algunos antes de crear uno nuevo.\n\n"
                    f"**Tus tickets activos:**\n" + 
                    "\n".join([f"• <#{ticket[0]}> ({ticket[1]})" for ticket in open_tickets]),
                    ephemeral=True
                )
                return
        
        # Crear nombre único del canal con timestamp - USAR USERNAME EN LUGAR DE DISPLAY_NAME
        timestamp = datetime.datetime.now().strftime("%m%d")
        channel_name = f"{category}-{user.name.lower()}-{timestamp}"  # Cambiado de display_name a name
        channel_name = "".join(c for c in channel_name if c.isalnum() or c in ('-', '_')).lower()[:50]
        
        # Verificar si ya existe un canal con ese nombre
        counter = 1
        original_name = channel_name
        while discord.utils.get(guild.channels, name=channel_name):
            channel_name = f"{original_name}-{counter}"
            counter += 1
        
        # Configurar permisos del canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        }
        
        # Agregar permisos para admins y owners
        for admin_id in ADMIN_IDS + OWNER_IDS:
            admin_member = guild.get_member(admin_id)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                    manage_channels=True
                )
        
        try:
            # Buscar o crear categoría para tickets
            ticket_category = discord.utils.get(guild.categories, name="🎫 TICKETS")
            if not ticket_category:
                ticket_category = await guild.create_category("🎫 TICKETS")
            
            # Crear el canal
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=ticket_category,
                overwrites=overwrites,
                topic=f"🎫 Ticket de {category} • Usuario: {user.display_name} • ID: {user.id}"
            )
            
            # Registrar en base de datos
            if tickets_cog:
                tickets_cog.create_ticket_record(
                    channel_id=ticket_channel.id,
                    user_id=user.id,
                    category=category,
                    status="abierto"
                )
            
            # Crear embed inicial más detallado
            embed = discord.Embed(
                title=f"🎫 Ticket de {category.title()} Creado",
                description=f"¡Hola {user.mention}! 👋\n\n"
                           f"Tu ticket ha sido creado exitosamente. Un miembro del staff te atenderá pronto.\n\n"
                           f"**📋 Información del Ticket:**\n"
                           f"• **Categoría:** {category.title()}\n"
                           f"• **Canal:** {ticket_channel.mention}\n"
                           f"• **Creado:** {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}\n\n"
                           f"**📝 Mientras esperas:**\n"
                           f"• Describe tu problema con el mayor detalle posible\n"
                           f"• Proporciona capturas de pantalla si es necesario\n"
                           f"• Se paciente, te responderemos lo antes posible",
                color=0x00ff88,
                timestamp=datetime.datetime.now()
            )
            
            # Agregar campo específico según categoría
            category_info = {
                "compras": "💰 Incluye detalles del producto que deseas comprar y tu método de pago preferido.",
                "ayuda": "❓ Explica el problema que tienes y qué has intentado hacer para resolverlo.",
                "reportes": "🚨 Describe el bug detalladamente y los pasos para reproducirlo.",
                "sugerencias": "💡 Comparte tu idea y explica cómo podría mejorar el servidor.",
                "personalizado": "🎯 Explica tu consulta con el mayor detalle posible."
            }
            
            embed.add_field(
                name=f"{['💰','❓','🚨','💡','🎯'][['compras','ayuda','reportes','sugerencias','personalizado'].index(category)]} Información específica:",
                value=category_info.get(category, "Describe tu consulta detalladamente."),
                inline=False
            )
            
            embed.set_footer(
                text=f"Ticket ID: {ticket_channel.id} • Usa los botones para gestionar el ticket",
                icon_url=user.display_avatar.url
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            # Crear vista con botones mejorados (SIN el botón de agregar usuario)
            view = TicketControlView(ticket_channel.id, category, user.id)
            
            # Crear menciones de owners y mensaje personalizado
            owner_mentions = " ".join([f"<@{owner_id}>" for owner_id in OWNER_IDS])
            owner_role_mention = f"<@&1400106792280658070>"
            
            # Mensaje de bienvenida personalizado
            welcome_msg = (
                f"{owner_role_mention} vengan a la brevedad que {user.mention} abrió su ticket.\n\n"
                f"👋 **¡Bienvenido a tu ticket {user.mention}!**\n\n"
                f"Un owner te atenderá muy pronto. Por favor mantén la paciencia mientras revisamos tu consulta.\n\n"
                f"📌 **Mientras esperas:**\n"
                f"• Describe tu problema con detalle\n"
                f"• Adjunta capturas si es necesario\n"
                f"• Mantén un lenguaje respetuoso\n\n"
                f"⏰ **Los owners serán notificados inmediatamente**"
            )
            
            # Enviar mensajes en el canal del ticket
            await ticket_channel.send(content=welcome_msg)
            await ticket_channel.send(embed=embed, view=view)
            
            # Notificar al staff en el canal de logs
            staff_embed = discord.Embed(
                title="🆕 Nuevo Ticket Creado",
                description=f"**Usuario:** {user.mention} (`{user.id}`)\n"
                           f"**Categoría:** {category.title()}\n"
                           f"**Canal:** {ticket_channel.mention}",
                color=0x00ff88,
                timestamp=datetime.datetime.now()
            )
            staff_embed.set_thumbnail(url=user.display_avatar.url)
            
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=staff_embed)
            
            # Responder al usuario
            await interaction.response.send_message(
                f"✅ **¡Ticket creado exitosamente!**\n"
                f"🎫 Canal: {ticket_channel.mention}\n"
                f"📋 Categoría: **{category.title()}**\n\n"
                f"Te hemos enviado toda la información en el canal del ticket.",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Error de permisos**\n"
                "No tengo los permisos necesarios para crear canales o categorías.\n"
                "Contacta con un administrador.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ **Error inesperado**\n"
                f"Ocurrió un error al crear el ticket: `{str(e)}`\n"
                f"Por favor, contacta con un administrador.",
                ephemeral=True
            )

class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

class TicketControlView(discord.ui.View):
    def __init__(self, channel_id, category, user_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.category = category
        self.user_id = user_id
        self.claimed_by = None

    def is_staff(self, user_id):
        return user_id in ADMIN_IDS or user_id in OWNER_IDS

    def is_owner(self, user_id):
        return user_id in OWNER_IDS
    
    def has_owner_role(self, member):
        """Verificar si el miembro tiene el rol de owner"""
        return any(role.id == OWNER_ROLE_ID for role in member.roles)
    
    def is_staff_or_owner_role(self, member):
        """Verificar si es staff por ID o tiene rol de owner"""
        return self.is_staff(member.id) or self.has_owner_role(member)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.primary, emoji="👋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar permisos (por ID o por rol)
        has_permission = self.is_staff_or_owner_role(interaction.user)
        
        print(f"Usuario {interaction.user.id} intentando reclamar.")
        print(f"Es staff por ID: {self.is_staff(interaction.user.id)}")
        print(f"Tiene rol de owner: {self.has_owner_role(interaction.user)}")
        print(f"Permiso final: {has_permission}")
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ **Solo el staff puede reclamar tickets**\n"
                "Esta función está reservada para administradores y owners.",
                ephemeral=True
            )
            return
        
        if self.claimed_by:
            claimed_user = interaction.guild.get_member(self.claimed_by)
            claimed_name = claimed_user.display_name if claimed_user else f"Usuario {self.claimed_by}"
            await interaction.response.send_message(
                f"❌ **Ticket ya reclamado**\n"
                f"Este ticket ya fue reclamado por **{claimed_name}**.\n"
                f"Si necesitas ayuda, puedes contactar con ellos directamente.",
                ephemeral=True
            )
            return
        
        self.claimed_by = interaction.user.id
        
        # Actualizar base de datos
        tickets_cog = interaction.client.get_cog('Tickets')
        if tickets_cog:
            tickets_cog.update_ticket_claim(self.channel_id, interaction.user.id)
        
        # Crear embed de reclamo
        embed = discord.Embed(
            title="👋 Ticket Reclamado",
            description=f"**{interaction.user.display_name}** se ha hecho cargo de este ticket.\n\n"
                       f"🔹 **Staff asignado:** {interaction.user.mention}\n"
                       f"🔹 **Tiempo:** {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
            color=0xffaa00,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Actualizar botón
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.disabled = True
        button.emoji = "✅"
        
        # MENSAJE DE SALUDO PERSONAL FUERA DEL EMBED
        user_mention = interaction.guild.get_member(self.user_id).mention
        personal_greeting = f"{user_mention}, un miembro del equipo ya está aquí.\n<@{interaction.user.id}> se encargará de ayudarte."
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)
        await interaction.followup.send(content=personal_greeting)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission = self.is_staff_or_owner_role(interaction.user) or interaction.user.id == self.user_id
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ **Sin permisos**\n"
                "Solo el staff, owners o el creador del ticket pueden cerrarlo.",
                ephemeral=True
            )
            return
        
        # Confirmación mejorada
        confirm_embed = discord.Embed(
            title="⚠️ Confirmar Cierre de Ticket",
            description="**¿Estás seguro de que quieres cerrar este ticket?**\n\n"
                       f"🔸 **Ticket ID:** `{self.channel_id}`\n"
                       f"🔸 **Categoría:** {self.category.title()}\n"
                       f"🔸 **Usuario:** <@{self.user_id}>\n\n"
                       f"⚠️ **Esta acción:**\n"
                       f"• Cerrará permanentemente el ticket\n"
                       f"• Eliminará el canal en 10 segundos\n"
                       f"• Guardará un registro en los logs\n"
                       f"• **NO se puede deshacer**",
            color=0xff6b6b
        )
        confirm_embed.set_footer(text="Tienes 60 segundos para decidir")
        
        confirm_view = ConfirmCloseView(self.channel_id, self.category, self.user_id, self.claimed_by)
        
        await interaction.response.send_message(
            embed=confirm_embed,
            view=confirm_view,
            ephemeral=True
        )

    # BOTÓN DE AGREGAR USUARIO ELIMINADO - Ya no existe en la vista

class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel_id, category, user_id, claimed_by):
        super().__init__(timeout=60)
        self.channel_id = channel_id
        self.category = category
        self.user_id = user_id
        self.claimed_by = claimed_by

    @discord.ui.button(label="Sí, cerrar ticket", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        
        # Actualizar base de datos
        tickets_cog = interaction.client.get_cog('Tickets')
        if tickets_cog:
            tickets_cog.close_ticket_record(self.channel_id, interaction.user.id)
        
        # Calcular duración del ticket
        creation_time = channel.created_at
        duration = datetime.datetime.now(datetime.timezone.utc) - creation_time
        duration_str = str(duration).split('.')[0]  # Remover microsegundos
        
        # Enviar log detallado al canal de logs
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="🔒 Ticket Cerrado",
                color=0xff4757,
                timestamp=datetime.datetime.now()
            )
            log_embed.add_field(name="👤 Usuario", value=f"<@{self.user_id}>", inline=True)
            log_embed.add_field(name="📂 Categoría", value=self.category.title(), inline=True)
            log_embed.add_field(name="📝 Canal", value=f"#{channel.name}", inline=True)
            log_embed.add_field(name="🔒 Cerrado por", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="⏱️ Duración", value=duration_str, inline=True)
            if self.claimed_by:
                log_embed.add_field(name="👋 Reclamado por", value=f"<@{self.claimed_by}>", inline=True)
            log_embed.set_footer(
                text=f"Ticket ID: {self.channel_id}",
                icon_url=interaction.user.display_avatar.url
            )
            
            await log_channel.send(embed=log_embed)
        
        # Mensaje de cierre con cuenta regresiva
        close_embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"**Este ticket ha sido cerrado por {interaction.user.mention}**\n\n"
                       f"📊 **Resumen:**\n"
                       f"• **Duración:** {duration_str}\n"
                       f"• **Categoría:** {self.category.title()}\n"
                       f"• **Usuario:** <@{self.user_id}>\n\n"
                       f"🗑️ **El canal será eliminado en 10 segundos...**\n"
                       f"¡Gracias por usar nuestro sistema de tickets!",
            color=0xff4757,
            timestamp=datetime.datetime.now()
        )
        close_embed.set_footer(text="Sistema de Tickets - Cerrando...")
        
        await interaction.response.edit_message(embed=close_embed, view=None)
        
        # Cuenta regresiva visual
        for i in range(9, 0, -1):
            close_embed.description = (
                f"**Este ticket ha sido cerrado por {interaction.user.mention}**\n\n"
                f"📊 **Resumen:**\n"
                f"• **Duración:** {duration_str}\n"
                f"• **Categoría:** {self.category.title()}\n"
                f"• **Usuario:** <@{self.user_id}>\n\n"
                f"🗑️ **El canal será eliminado en {i} segundos...**\n"
                f"¡Gracias por usar nuestro sistema de tickets!"
            )
            try:
                await interaction.edit_original_response(embed=close_embed)
                await asyncio.sleep(1)
            except:
                break
        
        # Eliminar canal
        try:
            await channel.delete(reason=f"Ticket cerrado por {interaction.user} - ID: {self.channel_id}")
        except:
            pass

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="❌ Cierre Cancelado",
            description="El ticket seguirá abierto.\nPuedes intentar cerrarlo nuevamente cuando lo desees.",
            color=0x95a5a6
        )
        await interaction.response.edit_message(
            embed=cancel_embed,
            view=None
        )

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_database()

    def init_database(self):
        """Inicializar la base de datos SQLite con esquema mejorado"""
        if not os.path.exists('tickets.db'):
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER UNIQUE,
                    user_id INTEGER,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    claimed_by INTEGER,
                    closed_by INTEGER,
                    status TEXT DEFAULT 'abierto',
                    priority TEXT DEFAULT 'normal'
                )
            ''')
            
            # Tabla para mensajes del ticket (opcional, para futuras funciones)
            cursor.execute('''
                CREATE TABLE ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER,
                    user_id INTEGER,
                    message_content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id)
                )
            ''')
            
            conn.commit()
            conn.close()

    def create_ticket_record(self, channel_id, user_id, category, status):
        """Crear registro de ticket en la base de datos"""
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tickets (channel_id, user_id, category, status)
                VALUES (?, ?, ?, ?)
            ''', (channel_id, user_id, category, status))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error al crear registro de ticket: {e}")

    def update_ticket_claim(self, channel_id, claimed_by):
        """Actualizar quien reclamó el ticket"""
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tickets SET claimed_by = ? WHERE channel_id = ?
            ''', (claimed_by, channel_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error al actualizar reclamo de ticket: {e}")

    def close_ticket_record(self, channel_id, closed_by):
        """Cerrar ticket en la base de datos"""
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tickets 
                SET status = 'cerrado', closed_at = CURRENT_TIMESTAMP, closed_by = ?
                WHERE channel_id = ?
            ''', (closed_by, channel_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error al cerrar ticket: {e}")

    def get_user_open_tickets(self, user_id):
        """Obtener tickets abiertos de un usuario"""
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT channel_id, category FROM tickets 
                WHERE user_id = ? AND status = 'abierto'
            ''', (user_id,))
            tickets = cursor.fetchall()
            conn.close()
            return tickets
        except Exception as e:
            print(f"❌ Error al obtener tickets del usuario: {e}")
            return []

    # Comando principal para crear el panel de tickets
    @commands.command(name="ticket_setup", aliases=["setup_tickets", "crear_panel"])
    @commands.has_permissions(administrator=True)
    async def setup_ticket_panel(self, ctx):
        """Crear el panel principal de tickets"""
        if ctx.channel.id != STAFF_CHANNEL_ID:
            await ctx.send(f"❌ Este comando solo se puede usar en <#{STAFF_CHANNEL_ID}>")
            return
            
        # Canal donde se enviará el panel
        panel_channel = self.bot.get_channel(TICKET_PANEL_CHANNEL_ID)
        if not panel_channel:
            await ctx.send(f"❌ No se encontró el canal de tickets <#{TICKET_PANEL_CHANNEL_ID}>")
            return
        
        # Crear embed principal del panel
        embed = discord.Embed(
            title="🎫 Sistema de Tickets de Soporte",
            description="¡Bienvenido al sistema de tickets! 👋\n\n"
                       "**¿Necesitas ayuda?** Selecciona una categoría abajo para crear tu ticket personalizado.\n\n"
                       "🔹 **Tu ticket será completamente privado**\n"
                       "🔹 **Solo tú y el staff podrán verlo**\n"
                       "🔹 **Respuesta promedio: 5-30 minutos**\n"
                       "🔹 **Límite: 3 tickets abiertos por usuario**",
            color=0x00d4ff
        )
        
        embed.add_field(
            name="📋 Categorías Disponibles:",
            value="💰 **Compras** - Productos, precios y métodos de pago\n"
                  "❓ **Ayuda** - Soporte técnico y resolución de problemas\n"
                  "🚨 **Reportes** - Reportar bugs, errores o problemas\n"
                  "💡 **Sugerencias** - Ideas para mejorar el servidor\n"
                  "🎯 **Personalizado** - Otras consultas o temas específicos",
            inline=False
        )
        
        embed.add_field(
            name="📝 Consejos para un mejor soporte:",
            value="• **Sé específico** - Explica tu problema detalladamente\n"
                  "• **Adjunta archivos** - Screenshots, logs, etc. si es necesario\n"
                  "• **Ten paciencia** - El staff te atenderá lo antes posible\n"
                  "• **Mantén el respeto** - Un buen ambiente beneficia a todos",
            inline=False
        )
        
        embed.set_footer(
            text=f"Sistema de Tickets • {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else self.bot.user.display_avatar.url
        )
        embed.set_image(url="https://via.placeholder.com/400x100/00d4ff/ffffff?text=Sistema+de+Tickets")
        
        # Vista con select menu
        view = TicketCategoryView()
        
        try:
            # Enviar al canal designado
            message = await panel_channel.send(embed=embed, view=view)
            
            # Confirmar en el canal de staff
            success_embed = discord.Embed(
                title="✅ Panel de Tickets Creado",
                description=f"**Panel enviado a:** {panel_channel.mention}\n"
                           f"**Mensaje ID:** `{message.id}`\n"
                           f"**Configuración activa ✅**",
                color=0x00ff88
            )
            success_embed.add_field(
                name="📊 Configuración:",
                value=f"**Admins:** {len(ADMIN_IDS)} configurados\n"
                      f"**Owners:** {len(OWNER_IDS)} configurados\n"
                      f"**Canal de logs:** <#{LOG_CHANNEL_ID}>\n"
                      f"**Canal del panel:** <#{TICKET_PANEL_CHANNEL_ID}>",
                inline=False
            )
            
            await ctx.send(embed=success_embed)
            
        except discord.Forbidden:
            await ctx.send(
                f"❌ **Error de permisos**\n"
                f"No tengo permisos para enviar mensajes en {panel_channel.mention}\n"
                f"Verifica que tenga los permisos necesarios."
            )
        except Exception as e:
            await ctx.send(f"❌ **Error inesperado:** `{str(e)}`")

    @commands.command(name="ticket_stats", aliases=["stats_tickets", "estadisticas"])
    @commands.has_permissions(manage_messages=True)
    async def ticket_stats(self, ctx, user: discord.Member = None):
        """Ver estadísticas detalladas de tickets"""
        if ctx.channel.id != STAFF_CHANNEL_ID:
            await ctx.send(f"❌ Este comando solo se puede usar en <#{STAFF_CHANNEL_ID}>")
            return
        
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            
            if user:
                # Estadísticas de usuario específico
                cursor.execute('''
                    SELECT category, COUNT(*), 
                           SUM(CASE WHEN status = 'abierto' THEN 1 ELSE 0 END) as abiertos,
                           SUM(CASE WHEN status = 'cerrado' THEN 1 ELSE 0 END) as cerrados
                    FROM tickets WHERE user_id = ? GROUP BY category
                ''', (user.id,))
                
                embed = discord.Embed(
                    title=f"📊 Estadísticas de {user.display_name}",
                    description=f"**Usuario:** {user.mention}\n**ID:** `{user.id}`",
                    color=0x3498db
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                
            else:
                # Estadísticas generales
                cursor.execute('''
                    SELECT category, COUNT(*), 
                           SUM(CASE WHEN status = 'abierto' THEN 1 ELSE 0 END) as abiertos,
                           SUM(CASE WHEN status = 'cerrado' THEN 1 ELSE 0 END) as cerrados
                    FROM tickets GROUP BY category
                ''')
                
                embed = discord.Embed(
                    title="📊 Estadísticas Generales de Tickets",
                    description="**Resumen completo del sistema de tickets**",
                    color=0x2ecc71
                )
            
            results = cursor.fetchall()
            
            if not results:
                embed.add_field(
                    name="📭 Sin datos",
                    value="No hay tickets registrados." + (f" para {user.mention}" if user else ""),
                    inline=False
                )
            else:
                total_tickets = 0
                total_open = 0
                total_closed = 0
                
                stats_text = ""
                for category, total, abiertos, cerrados in results:
                    emoji = {
                        "compras": "💰", 
                        "ayuda": "❓", 
                        "reportes": "🚨", 
                        "sugerencias": "💡",
                        "personalizado": "🎯"
                    }.get(category, "🎫")
                    
                    stats_text += f"{emoji} **{category.title()}**\n"
                    stats_text += f"   📈 Total: **{total}** | 🟢 Abiertos: **{abiertos}** | ✅ Cerrados: **{cerrados}**\n\n"
                    
                    total_tickets += total
                    total_open += abiertos
                    total_closed += cerrados
                
                embed.add_field(
                    name="📈 Estadísticas por Categoría",
                    value=stats_text,
                    inline=False
                )
                
                # Calcular porcentajes
                if total_tickets > 0:
                    closed_percentage = round((total_closed / total_tickets) * 100, 1)
                    open_percentage = round((total_open / total_tickets) * 100, 1)
                else:
                    closed_percentage = open_percentage = 0
                
                embed.add_field(
                    name="📊 Resumen Total",
                    value=f"🎫 **Total de tickets:** {total_tickets}\n"
                          f"🟢 **Abiertos:** {total_open} ({open_percentage}%)\n"
                          f"✅ **Cerrados:** {total_closed} ({closed_percentage}%)",
                    inline=True
                )
                
                # Estadísticas adicionales si es general
                if not user:
                    # Top usuarios con más tickets
                    cursor.execute('''
                        SELECT user_id, COUNT(*) as total_tickets 
                        FROM tickets 
                        GROUP BY user_id 
                        ORDER BY total_tickets DESC 
                        LIMIT 5
                    ''')
                    top_users = cursor.fetchall()
                    
                    if top_users:
                        top_users_text = ""
                        for i, (user_id, count) in enumerate(top_users, 1):
                            user_obj = self.bot.get_user(user_id)
                            name = user_obj.display_name if user_obj else f"Usuario {user_id}"
                            top_users_text += f"{i}. **{name}** - {count} tickets\n"
                        
                        embed.add_field(
                            name="👑 Top 5 Usuarios",
                            value=top_users_text,
                            inline=True
                        )
                    
                    # Staff más activo
                    cursor.execute('''
                        SELECT claimed_by, COUNT(*) as claims 
                        FROM tickets 
                        WHERE claimed_by IS NOT NULL 
                        GROUP BY claimed_by 
                        ORDER BY claims DESC 
                        LIMIT 5
                    ''')
                    top_staff = cursor.fetchall()
                    
                    if top_staff:
                        top_staff_text = ""
                        for i, (staff_id, count) in enumerate(top_staff, 1):
                            staff_obj = self.bot.get_user(staff_id)
                            name = staff_obj.display_name if staff_obj else f"Staff {staff_id}"
                            top_staff_text += f"{i}. **{name}** - {count} reclamados\n"
                        
                        embed.add_field(
                            name="⭐ Staff Más Activo",
                            value=top_staff_text,
                            inline=True
                        )
            
            embed.set_footer(
                text=f"📅 Generado el {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
                icon_url=ctx.author.display_avatar.url
            )
            
            conn.close()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ **Error al obtener estadísticas:** `{str(e)}`")

    @commands.command(name="ticket_close", aliases=["cerrar_ticket", "close_ticket"])
    @commands.has_permissions(manage_messages=True)
    async def force_close_ticket(self, ctx, channel: discord.TextChannel = None):
        """Forzar el cierre de un ticket específico"""
        if ctx.channel.id != STAFF_CHANNEL_ID:
            await ctx.send(f"❌ Este comando solo se puede usar en <#{STAFF_CHANNEL_ID}>")
            return
        
        target_channel = channel or ctx.channel
        
        # Verificar si es un canal de ticket
        if not target_channel.name.startswith(('compras-', 'ayuda-', 'reportes-', 'sugerencias-', 'personalizado-')):
            await ctx.send(f"❌ {target_channel.mention} no parece ser un canal de ticket válido.")
            return
        
        try:
            # Obtener información del ticket de la base de datos
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, category, claimed_by FROM tickets 
                WHERE channel_id = ? AND status = 'abierto'
            ''', (target_channel.id,))
            ticket_info = cursor.fetchone()
            
            if not ticket_info:
                await ctx.send(f"❌ No se encontró información del ticket para {target_channel.mention}")
                return
            
            user_id, category, claimed_by = ticket_info
            
            # Cerrar en la base de datos
            self.close_ticket_record(target_channel.id, ctx.author.id)
            
            # Crear embed de cierre forzado
            embed = discord.Embed(
                title="🔒 Ticket Cerrado por Staff",
                description=f"**Este ticket ha sido cerrado por {ctx.author.mention}**\n\n"
                           f"📋 **Información:**\n"
                           f"• **Usuario:** <@{user_id}>\n"
                           f"• **Categoría:** {category.title()}\n"
                           f"• **Cerrado por:** {ctx.author.mention}\n\n"
                           f"🗑️ **El canal será eliminado en 5 segundos...**",
                color=0xff4757,
                timestamp=datetime.datetime.now()
            )
            
            await target_channel.send(embed=embed)
            
            # Log del cierre forzado
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🔒 Ticket Cerrado (Forzado)",
                    color=0xff6b6b,
                    timestamp=datetime.datetime.now()
                )
                log_embed.add_field(name="👤 Usuario", value=f"<@{user_id}>", inline=True)
                log_embed.add_field(name="📂 Categoría", value=category.title(), inline=True)
                log_embed.add_field(name="📝 Canal", value=f"#{target_channel.name}", inline=True)
                log_embed.add_field(name="🔒 Cerrado por", value=ctx.author.mention, inline=True)
                log_embed.add_field(name="⚠️ Tipo", value="Cierre Forzado", inline=True)
                if claimed_by:
                    log_embed.add_field(name="👋 Reclamado por", value=f"<@{claimed_by}>", inline=True)
                log_embed.set_footer(text=f"Ticket ID: {target_channel.id}")
                
                await log_channel.send(embed=log_embed)
            
            # Confirmar en el canal de staff si es diferente
            if ctx.channel != target_channel:
                await ctx.send(f"✅ Ticket {target_channel.mention} cerrado exitosamente.")
            
            # Eliminar canal
            await asyncio.sleep(5)
            await target_channel.delete(reason=f"Ticket cerrado forzadamente por {ctx.author}")
            
            conn.close()
            
        except Exception as e:
            await ctx.send(f"❌ **Error al cerrar ticket:** `{str(e)}`")

    @commands.command(name="ticket_info", aliases=["info_ticket", "ticket_detalles"])
    @commands.has_permissions(manage_messages=True)
    async def ticket_info(self, ctx, channel: discord.TextChannel = None):
        """Ver información detallada de un ticket"""
        if ctx.channel.id != STAFF_CHANNEL_ID:
            await ctx.send(f"❌ Este comando solo se puede usar en <#{STAFF_CHANNEL_ID}>")
            return
        
        target_channel = channel or ctx.channel
        
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tickets WHERE channel_id = ?
            ''', (target_channel.id,))
            ticket = cursor.fetchone()
            
            if not ticket:
                await ctx.send(f"❌ No se encontró información del ticket para {target_channel.mention}")
                return
            
            # Desempaquetar información del ticket
            (ticket_id, channel_id, user_id, category, created_at, 
             closed_at, claimed_by, closed_by, status, priority) = ticket
            
            # Obtener objetos de usuario
            user = self.bot.get_user(user_id)
            claimer = self.bot.get_user(claimed_by) if claimed_by else None
            closer = self.bot.get_user(closed_by) if closed_by else None
            
            # Calcular duración
            created_time = datetime.datetime.fromisoformat(created_at)
            if closed_at:
                closed_time = datetime.datetime.fromisoformat(closed_at)
                duration = closed_time - created_time
            else:
                duration = datetime.datetime.now() - created_time
            
            duration_str = str(duration).split('.')[0]  # Remover microsegundos
            
            # Crear embed informativo
            embed = discord.Embed(
                title=f"🎫 Información del Ticket #{ticket_id}",
                description=f"**Estado:** {'✅ Cerrado' if status == 'cerrado' else '🟢 Abierto'}\n"
                           f"**Canal:** {target_channel.mention}",
                color=0xff4757 if status == 'cerrado' else 0x00ff88
            )
            
            embed.add_field(
                name="👤 Usuario",
                value=f"{user.mention if user else 'Usuario desconocido'}\n`{user_id}`",
                inline=True
            )
            
            embed.add_field(
                name="📂 Categoría",
                value=f"{'💰💡🚨❓🎯'[['compras','sugerencias','reportes','ayuda','personalizado'].index(category)] if category in ['compras','sugerencias','reportes','ayuda','personalizado'] else '🎫'} {category.title()}",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Duración",
                value=duration_str,
                inline=True
            )
            
            embed.add_field(
                name="📅 Creado",
                value=f"<t:{int(created_time.timestamp())}:F>\n<t:{int(created_time.timestamp())}:R>",
                inline=True
            )
            
            if claimed_by:
                embed.add_field(
                    name="👋 Reclamado por",
                    value=f"{claimer.mention if claimer else 'Usuario desconocido'}\n`{claimed_by}`",
                    inline=True
                )
            else:
                embed.add_field(
                    name="👋 Reclamado por",
                    value="*Sin reclamar*",
                    inline=True
                )
            
            if status == 'cerrado' and closed_at:
                closed_time = datetime.datetime.fromisoformat(closed_at)
                embed.add_field(
                    name="🔒 Cerrado",
                    value=f"<t:{int(closed_time.timestamp())}:F>\n<t:{int(closed_time.timestamp())}:R>",
                    inline=True
                )
                
                if closed_by:
                    embed.add_field(
                        name="🔒 Cerrado por",
                        value=f"{closer.mention if closer else 'Usuario desconocido'}\n`{closed_by}`",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🔒 Cerrado por",
                        value="*Desconocido*",
                        inline=True
                    )
            
            embed.set_footer(
                text=f"Ticket ID: {ticket_id} • Channel ID: {channel_id}",
                icon_url=user.display_avatar.url if user else None
            )
            embed.set_thumbnail(url=user.display_avatar.url if user else None)
            
            conn.close()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ **Error al obtener información:** `{str(e)}`")

    @commands.command(name="ticket_list", aliases=["lista_tickets", "tickets_abiertos"])
    @commands.has_permissions(manage_messages=True)
    async def list_tickets(self, ctx):
        """Listar todos los tickets abiertos"""
        if ctx.channel.id != STAFF_CHANNEL_ID:
            await ctx.send(f"❌ Este comando solo se puede usar en <#{STAFF_CHANNEL_ID}>")
            return
        
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT channel_id, user_id, category, created_at, claimed_by 
                FROM tickets 
                WHERE status = 'abierto' 
                ORDER BY created_at DESC
            ''')
            open_tickets = cursor.fetchall()
            
            if not open_tickets:
                embed = discord.Embed(
                    title="📭 No hay tickets abiertos",
                    description="¡Excelente trabajo! No hay tickets pendientes en este momento.",
                    color=0x2ecc71
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📋 Tickets Abiertos ({len(open_tickets)})",
                description="Lista de todos los tickets actualmente abiertos:",
                color=0x3498db
            )
            
            tickets_text = ""
            for i, (channel_id, user_id, category, created_at, claimed_by) in enumerate(open_tickets, 1):
                channel = self.bot.get_channel(channel_id)
                user = self.bot.get_user(user_id)
                claimer = self.bot.get_user(claimed_by) if claimed_by else None
                
                created_time = datetime.datetime.fromisoformat(created_at)
                time_ago = datetime.datetime.now() - created_time
                time_str = str(time_ago).split('.')[0]
                
                channel_mention = channel.mention if channel else f"Canal eliminado ({channel_id})"
                user_mention = user.mention if user else f"Usuario {user_id}"
                
                emoji = {'compras': '💰', 'ayuda': '❓', 'reportes': '🚨', 'sugerencias': '💡', 'personalizado': '🎯'}.get(category, '🎫')
                
                status_emoji = "👋" if claimed_by else "⏳"
                claimer_text = f" - {claimer.display_name}" if claimer else ""
                
                tickets_text += f"`{i:02d}.` {emoji} {channel_mention} | {user_mention}\n"
                tickets_text += f"      {status_emoji} {category.title()}{claimer_text} • {time_str} ago\n\n"
                
                # Dividir en múltiples embeds si es muy largo
                if len(tickets_text) > 1800:
                    embed.add_field(
                        name="🎫 Lista de Tickets",
                        value=tickets_text,
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    
                    # Crear nuevo embed para continuar
                    embed = discord.Embed(
                        title=f"📋 Tickets Abiertos (Continuación)",
                        color=0x3498db
                    )
                    tickets_text = ""
            
            if tickets_text:
                embed.add_field(
                    name="🎫 Lista de Tickets" + (" (Continuación)" if len(open_tickets) > 10 else ""),
                    value=tickets_text,
                    inline=False
                )
            
            # Agregar resumen
            claimed_count = sum(1 for ticket in open_tickets if ticket[4] is not None)
            unclaimed_count = len(open_tickets) - claimed_count
            
            embed.add_field(
                name="📊 Resumen",
                value=f"👋 **Reclamados:** {claimed_count}\n"
                      f"⏳ **Sin reclamar:** {unclaimed_count}\n"
                      f"🎫 **Total:** {len(open_tickets)}",
                inline=False
            )
            
            embed.set_footer(
                text=f"💡 Usa !ticket_info <canal> para ver detalles de un ticket específico",
                icon_url=ctx.author.display_avatar.url
            )
            
            conn.close()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ **Error al listar tickets:** `{str(e)}`")

    # Comando de ayuda personalizado
    @commands.command(name="help_ticket", aliases=["help_tickets", "ayuda_tickets"])
    async def help_ticket(self, ctx):
        """Mostrar ayuda del sistema de tickets"""
        embed = discord.Embed(
            title="🎫 Sistema de Tickets - Comandos de Staff",
            description="**Lista completa de comandos disponibles:**",
            color=0x9b59b6
        )
        
        embed.add_field(
            name="🛠️ Configuración",
            value="`!ticket_setup` - Crear el panel principal de tickets\n"
                  "`!help_ticket` - Mostrar esta ayuda",
            inline=False
        )
        
        embed.add_field(
            name="📊 Gestión y Estadísticas",
            value="`!ticket_stats [usuario]` - Ver estadísticas generales o de un usuario\n"
                  "`!ticket_list` - Listar todos los tickets abiertos\n"
                  "`!ticket_info [canal]` - Ver información detallada de un ticket",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Control de Tickets",
            value="`!ticket_close [canal]` - Forzar el cierre de un ticket\n"
                  "*(Los botones del panel también funcionan)*",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuración Actual",
            value=f"**📍 Canal del panel:** <#{TICKET_PANEL_CHANNEL_ID}>\n"
                  f"**📝 Canal de staff:** <#{STAFF_CHANNEL_ID}>\n"
                  f"**📋 Canal de logs:** <#{LOG_CHANNEL_ID}>\n"
                  f"**👑 Staff:** {len(ADMIN_IDS + OWNER_IDS)} configurados",
            inline=False
        )
        
        embed.set_footer(
            text="💡 Los comandos de staff solo funcionan en el canal designado",
            icon_url=ctx.bot.user.display_avatar.url
        )
        
        await ctx.send(embed=embed)

    # Comando de prueba mejorado
    @commands.command(name="ticket_test", aliases=["test_tickets"])
    @commands.has_permissions(administrator=True)
    async def ticket_test(self, ctx):
        """Comando de prueba completo para administradores"""
        embed = discord.Embed(
            title="✅ Sistema de Tickets - Prueba Completa",
            description="**Estado del sistema:**",
            color=0x2ecc71
        )
        
        # Verificar canales
        panel_channel = self.bot.get_channel(TICKET_PANEL_CHANNEL_ID)
        staff_channel = self.bot.get_channel(STAFF_CHANNEL_ID)
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        
        embed.add_field(
            name="📍 Canales",
            value=f"**Panel:** {panel_channel.mention if panel_channel else '❌ No encontrado'}\n"
                  f"**Staff:** {staff_channel.mention if staff_channel else '❌ No encontrado'}\n"
                  f"**Logs:** {log_channel.mention if log_channel else '❌ No encontrado'}",
            inline=True
        )
        
        # Verificar base de datos
        try:
            conn = sqlite3.connect('tickets.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tickets')
            total_tickets = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM tickets WHERE status = "abierto"')
            open_tickets = cursor.fetchone()[0]
            
            conn.close()
            db_status = "✅ Funcionando"
        except:
            total_tickets = "Error"
            open_tickets = "Error"
            db_status = "❌ Error"
        
        embed.add_field(
            name="💾 Base de Datos",
            value=f"**Estado:** {db_status}\n"
                  f"**Total tickets:** {total_tickets}\n"
                  f"**Tickets abiertos:** {open_tickets}",
            inline=True
        )
        
        # Verificar permisos
        permissions_ok = True
        required_perms = ['manage_channels', 'manage_messages', 'send_messages', 'embed_links']
        
        for channel in [panel_channel, staff_channel, log_channel]:
            if channel:
                perms = channel.permissions_for(ctx.guild.me)
                for perm in required_perms:
                    if not getattr(perms, perm, False):
                        permissions_ok = False
                        break
        
        embed.add_field(
            name="🔑 Permisos",
            value=f"**Estado:** {'✅ Correctos' if permissions_ok else '❌ Faltantes'}\n"
                  f"**Staff configurado:** {len(ADMIN_IDS + OWNER_IDS)} usuarios",
            inline=True
        )
        
        # Comandos disponibles
        embed.add_field(
            name="⚡ Comandos Disponibles",
            value="`!ticket_setup` - Crear panel\n"
                  "`!ticket_stats` - Estadísticas\n"
                  "`!ticket_list` - Listar tickets\n"
                  "`!help_ticket` - Ver ayuda",
            inline=False
        )
        
        embed.set_footer(
            text=f"🤖 Bot funcionando correctamente • Latencia: {round(self.bot.latency * 1000)}ms",
            icon_url=self.bot.user.display_avatar.url
        )
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))