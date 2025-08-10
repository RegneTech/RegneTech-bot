import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import datetime
from typing import Dict, Set, Optional, List

class ConfirmarTerminar(discord.ui.View):
    def __init__(self, canal_id: int, usuario_id: int):
        super().__init__(timeout=60)
        self.canal_id = canal_id
        self.usuario_id = usuario_id

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirmar_terminar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Embed de inicio del contador
        countdown_embed = discord.Embed(
            title="⏳ Cerrando Reseña",
            description=f"**La reseña se cerrará automáticamente en 10 segundos.**\n\n"
                       f"🔸 **Canal:** {interaction.channel.mention}\n"
                       f"🔸 **Usuario:** <@{self.usuario_id}>\n"
                       f"🔸 **Cerrado por:** {interaction.user.mention}\n\n"
                       f"⚠️ **Esta acción:**\n"
                       f"• Cerrará permanentemente la reseña\n"
                       f"• Eliminará el canal\n"
                       f"• Liberará al usuario del sistema\n"
                       f"• **NO se puede deshacer**",
            color=0xff6b6b,
            timestamp=datetime.datetime.now()
        )
        countdown_embed.set_footer(text="Cerrando reseña...")

        await interaction.response.edit_message(embed=countdown_embed, view=None)
        
        # Countdown de 10 segundos
        for i in range(10, 0, -1):
            countdown_embed.description = f"**La reseña se cerrará automáticamente en {i} segundos.**\n\n" \
                                        f"🔸 **Canal:** {interaction.channel.mention}\n" \
                                        f"🔸 **Usuario:** <@{self.usuario_id}>\n" \
                                        f"🔸 **Cerrado por:** {interaction.user.mention}\n\n" \
                                        f"⚠️ **Esta acción:**\n" \
                                        f"• Cerrará permanentemente la reseña\n" \
                                        f"• Eliminará el canal\n" \
                                        f"• Liberará al usuario del sistema\n" \
                                        f"• **NO se puede deshacer**"
            await interaction.edit_original_response(embed=countdown_embed)
            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

        # Liberar usuario del sistema
        usuario = interaction.guild.get_member(self.usuario_id)
        bot = interaction.client
        resenas_cog = bot.get_cog("Resenas")
        
        if resenas_cog and usuario:
            for vista in resenas_cog.vistas_activas.values():
                if usuario.id in vista.usuarios_con_resena:
                    vista.usuarios_con_resena.remove(usuario.id)
                    
                    class FakeInteraction:
                        def __init__(self, guild):
                            self.guild = guild
                    
                    fake_interaction = FakeInteraction(interaction.guild)
                    await vista.actualizar_mensaje_original(fake_interaction)

        # Eliminar el canal
        await interaction.channel.delete(reason=f"Reseña completada para {usuario.display_name if usuario else 'Usuario desconocido'}")

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar_terminar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="✅ Operación Cancelada",
            description="El cierre de la reseña ha sido cancelado.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=cancel_embed, view=None)

class ReseñasBotones(discord.ui.View):
    def __init__(self, usuario_id: int, staff_role_ids: List[int]):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.staff_role_ids = staff_role_ids
        self.reclamado_por = None

    @discord.ui.button(label="Reclamar", style=discord.ButtonStyle.success, emoji="👋")
    async def reclamar_resena(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que tenga algún rol de staff
        tiene_rol_staff = any(role.id in self.staff_role_ids for role in interaction.user.roles)
        if not tiene_rol_staff:
            embed_error = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los miembros del staff pueden reclamar reseñas.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        # Actualizar botón
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.disabled = True
        button.emoji = "✅"
        
        # Guardar quien reclamó
        self.reclamado_por = interaction.user.id
        
        # Crear embed de reclamo
        embed = discord.Embed(
            title="👋 Reseña Reclamada",
            description=f"**{interaction.user.display_name}** se ha hecho cargo de esta reseña.\n\n"
                       f"🔹 **Staff asignado:** {interaction.user.mention}\n"
                       f"🔹 **Tiempo:** {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
            color=0xffaa00,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Primero actualizar el mensaje original con el botón modificado
        await interaction.response.edit_message(view=self)
        
        # Enviar el embed de reclamo
        await interaction.followup.send(embed=embed)
        
        # Enviar mensaje adicional sin embed
        mensaje_adicional = f"{interaction.user.mention}, un miembro del equipo ya está aquí.\n{interaction.user.mention} se encargará de ayudarte con tu reseña."
        await interaction.followup.send(mensaje_adicional)

    @discord.ui.button(label="Terminar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def terminar_resena(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que tenga algún rol de staff
        tiene_rol_staff = any(role.id in self.staff_role_ids for role in interaction.user.roles)
        if not tiene_rol_staff:
            embed_error = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los miembros del staff pueden terminar reseñas.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        # Confirmación mejorada
        confirm_embed = discord.Embed(
            title="⚠️ Confirmar Cierre de Reseña",
            description="**¿Estás seguro de que quieres cerrar esta reseña?**\n\n"
                       f"🔸 **Canal:** {interaction.channel.mention}\n"
                       f"🔸 **Usuario:** <@{self.usuario_id}>\n"
                       f"🔸 **Staff:** {interaction.user.mention}\n\n"
                       f"⚠️ **Esta acción:**\n"
                       f"• Cerrará permanentemente la reseña\n"
                       f"• Eliminará el canal en 10 segundos\n"
                       f"• Liberará al usuario del sistema\n"
                       f"• **NO se puede deshacer**",
            color=0xff6b6b
        )
        confirm_embed.set_footer(text="Tienes 60 segundos para decidir")

        vista_confirmacion = ConfirmarTerminar(interaction.channel.id, self.usuario_id)
        await interaction.response.send_message(embed=confirm_embed, view=vista_confirmacion, ephemeral=True)

    @discord.ui.button(label="Llamar", style=discord.ButtonStyle.primary, emoji="📞")
    async def llamar_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que alguien haya reclamado la reseña
        if not self.reclamado_por:
            embed_error = discord.Embed(
                title="❌ Nadie ha reclamado",
                description="Primero alguien debe reclamar esta reseña.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        # Obtener el usuario que pidió la reseña y el que la reclamó
        usuario_resena = interaction.guild.get_member(self.usuario_id)
        staff_reclamo = interaction.guild.get_member(self.reclamado_por)
        
        nombre_usuario = usuario_resena.display_name if usuario_resena else "Usuario desconocido"
        
        # Mensaje de llamada
        mensaje = f"{staff_reclamo.mention if staff_reclamo else 'Staff'} **{nombre_usuario}** ya terminó su reseña, es hora de comprobarla."
        
        await interaction.response.send_message(mensaje)

class ResenasView(discord.ui.View):
    def __init__(self, resenas_disponibles: int, canal_resenas_id: int, staff_role_ids: List[int], mensaje_id: int = None):
        super().__init__(timeout=None)
        self.resenas_disponibles = resenas_disponibles
        self.resenas_originales = resenas_disponibles
        self.usuarios_con_resena: Set[int] = set()
        self.canal_resenas_id = canal_resenas_id
        self.staff_role_ids = staff_role_ids
        self.mensaje_id = mensaje_id
        
        self.actualizar_boton()
    
    def actualizar_boton(self):
        """Actualiza el estado del botón según los cupos disponibles"""
        boton = self.children[0] if self.children else None
        
        if self.resenas_disponibles > 0:
            if boton:
                boton.label = "Quiero reseñas"
                boton.disabled = False
                boton.style = discord.ButtonStyle.primary
        else:
            if boton:
                boton.label = "Reseñas agotadas"
                boton.disabled = True
                boton.style = discord.ButtonStyle.secondary
    
    async def actualizar_mensaje_original(self, interaction: discord.Interaction):
        """Actualiza el mensaje original con el nuevo estado"""
        try:
            embed_actualizado = discord.Embed(
                title="📝 Sistema de Reseñas",
                description=f"Hay **{self.resenas_disponibles}** reseñas disponibles de **{self.resenas_originales}** totales.",
                color=0x0099ff
            )
            
            if self.resenas_disponibles > 0:
                embed_actualizado.add_field(
                    name="Estado", 
                    value="✅ Disponible", 
                    inline=True
                )
            else:
                embed_actualizado.add_field(
                    name="Estado", 
                    value="❌ Agotado", 
                    inline=True
                )
            
            embed_actualizado.add_field(
                name="Instrucciones", 
                value="Presiona el botón para solicitar una reseña", 
                inline=True
            )
            
            canal = interaction.guild.get_channel(self.canal_resenas_id)
            if canal and self.mensaje_id:
                try:
                    mensaje = await canal.fetch_message(self.mensaje_id)
                    await mensaje.edit(embed=embed_actualizado, view=self)
                except discord.NotFound:
                    nuevo_mensaje = await canal.send(embed=embed_actualizado, view=self)
                    self.mensaje_id = nuevo_mensaje.id
                except discord.HTTPException:
                    pass
            
        except Exception as e:
            print(f"Error al actualizar mensaje: {e}")
    
    @discord.ui.button(label="Quiero reseñas", style=discord.ButtonStyle.primary)
    async def solicitar_resena(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Maneja la solicitud de reseña cuando se presiona el botón"""
        
        if interaction.user.id in self.usuarios_con_resena:
            embed = discord.Embed(
                title="⚠️ Reseña ya solicitada",
                description="Ya tienes una reseña en curso. No puedes solicitar otra hasta que se complete la actual.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if self.resenas_disponibles <= 0:
            embed = discord.Embed(
                title="❌ Sin cupos disponibles",
                description="Ya no hay reseñas disponibles en este momento.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            
            # Buscar o crear la categoría "📚 RESENAS"
            categoria = discord.utils.get(guild.categories, name="📚 RESENAS")
            if not categoria:
                categoria = await guild.create_category("📚 RESENAS")
            
            # Configurar permisos del canal (sin menciones para el usuario)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    mention_everyone=False
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True
                )
            }
            
            # Agregar permisos para los roles de staff
            for role_id in self.staff_role_ids:
                staff_role = guild.get_role(role_id)
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=True
                    )
            
            # Crear el canal
            nombre_canal = f"resenas-{interaction.user.name}".replace(" ", "-").lower()
            nombre_canal = ''.join(c for c in nombre_canal if c.isalnum() or c in '-_')
            
            canal_ticket = await guild.create_text_channel(
                name=nombre_canal,
                overwrites=overwrites,
                category=categoria,
                topic=f"Reseña para {interaction.user.display_name}"
            )
            
            # Crear embed de instrucciones
            embed_instrucciones = discord.Embed(
                title="📝 Instrucciones para dejar una reseña en Google",
                description="Para que tu reseña sea válida y profesional, sigue estos dos pasos:",
                color=0x4285f4
            )
            
            embed_instrucciones.add_field(
                name="1️⃣ Cambia tu nombre de Google",
                value="Si usas un nombre como \"xXPepeproXx\", tu reseña puede parecer falsa. Debes usar tu nombre real.\n"
                      "• Abre este enlace: https://myaccount.google.com/profile\n"
                      "• Haz clic en tu nombre y cámbialo por uno real (ej: Laura Morales o Javier Ortega).\n"
                      "• Evita apodos o nombres de videojuegos.\n"
                      "• Guarda los cambios.",
                inline=False
            )
            
            embed_instrucciones.add_field(
                name="2️⃣ Deja la reseña correctamente",
                value="• Un miembro del equipo te pasará el enlace del sitio en Google Maps.\n"
                      "• Ábrelo y pulsa \"Escribir una reseña\".\n"
                      "• Pon 5 estrellas.\n"
                      "• Escribe un comentario creíble, relacionado con el local (ej: buena atención, limpieza, precio, etc.).\n\n"
                      "**Tu nombre y reseña serán visibles para todos. Asegúrate de que parezca real y profesional.**",
                inline=False
            )
            
            # Crear menciones de los roles de staff
            menciones_staff = []
            for role_id in self.staff_role_ids:
                staff_role = guild.get_role(role_id)
                if staff_role:
                    menciones_staff.append(staff_role.mention)
            
            # Mensaje con menciones
            mensaje_menciones = f"{interaction.user.mention}"
            if menciones_staff:
                mensaje_menciones += f" {' '.join(menciones_staff)}"
            
            # Crear vista con botones para el canal
            vista_botones = ReseñasBotones(interaction.user.id, self.staff_role_ids)
            
            await canal_ticket.send(mensaje_menciones, embed=embed_instrucciones, view=vista_botones)
            
            # Actualizar el estado
            self.resenas_disponibles -= 1
            self.usuarios_con_resena.add(interaction.user.id)
            
            # Actualizar el botón
            self.actualizar_boton()
            
            # Actualizar el mensaje original
            await self.actualizar_mensaje_original(interaction)
            
            # Responder al usuario
            embed_respuesta = discord.Embed(
                title="✅ Canal creado exitosamente",
                description=f"Se ha creado tu canal de reseña: {canal_ticket.mention}",
                color=0x00ff00
            )
            
            await interaction.followup.send(embed=embed_respuesta, ephemeral=True)
            
        except discord.Forbidden:
            embed_error = discord.Embed(
                title="❌ Error de permisos",
                description="No tengo permisos suficientes para crear canales o categorías.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed_error, ephemeral=True)
        
        except Exception as e:
            embed_error = discord.Embed(
                title="❌ Error inesperado",
                description=f"Ocurrió un error al crear el canal: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed_error, ephemeral=True)

class Resenas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vistas_activas: Dict[int, ResenasView] = {}
        
        # 🔧 CONFIGURACIÓN MANUAL - CAMBIA ESTOS IDs POR LOS DE TU SERVIDOR
        self.CANAL_RESENAS_ID = 1400106793551663190  # ID del canal donde se publican las reseñas
        self.ROL_NOTIFICACION_RESENAS_ID = 1400106792196898891 # ID del rol que se menciona al usuario al publicar reseñas
        self.STAFF_ROLE_IDS = [
            1400106792280658070,  # ID del primer rol de staff/moderación (OWNER)
        ]
    
    @commands.command(name="help_resenas")
    @commands.has_permissions(manage_channels=True)
    async def help_resenas(self, ctx):
        """Muestra todos los comandos disponibles del sistema de reseñas"""
        
        embed = discord.Embed(
            title="📖 Ayuda - Sistema de Reseñas",
            description="Lista completa de comandos disponibles para el sistema de reseñas.",
            color=0x4285f4,
            timestamp=datetime.datetime.now()
        )
        
        # Comandos principales
        embed.add_field(
            name="🚀 **Comandos Principales**",
            value=(
                "`!resenas <número>` - Inicia el sistema con el número especificado de reseñas\n"
                "• **Ejemplo:** `!resenas 5`\n"
                "• **Permisos:** Administrador\n"
                "• **Rango:** 1-50 reseñas\n\n"
                
                "`!estado_resenas` - Muestra el estado actual de todas las sesiones activas\n"
                "• **Permisos:** Administrador\n"
                "• **Info mostrada:** Cupos disponibles, usuarios activos\n\n"
            ),
            inline=False
        )
        
        # Comandos de gestión
        embed.add_field(
            name="⚙️ **Comandos de Gestión**",
            value=(
                "`!cerrar_resena [@usuario]` - Cierra la reseña de un usuario\n"
                "• **Uso 1:** `!cerrar_resena @Usuario` (desde cualquier canal)\n"
                "• **Uso 2:** `!cerrar_resena` (dentro del canal de reseña)\n"
                "• **Permisos:** Gestionar canales\n\n"
                
                "`!reset_resenas` - Reinicia completamente el sistema\n"
                "• **Efecto:** Elimina todas las sesiones activas\n"
                "• **Permisos:** Administrador\n"
                "• **⚠️ Irreversible**\n\n"
            ),
            inline=False
        )
        
        # Comandos de mantenimiento
        embed.add_field(
            name="🔧 **Comandos de Mantenimiento**",
            value=(
                "`!actualizar_resenas` - Fuerza la actualización de mensajes\n"
                "• **Uso:** Cuando los mensajes no se actualizan correctamente\n"
                "• **Permisos:** Administrador\n\n"
                
                "`!config_info` - Muestra la configuración actual\n"
                "• **Info mostrada:** Canal configurado, roles de staff, sistemas activos\n"
                "• **Permisos:** Administrador\n\n"
            ),
            inline=False
        )
        
        # Comandos de utilidad
        embed.add_field(
            name="🛠️ **Comandos de Utilidad**",
            value=(
                "`!resenas_test` - Verifica que el módulo funcione correctamente\n"
                "• **Uso:** Diagnóstico del sistema\n"
                "• **Permisos:** Administrador\n\n"
                
                "`!help_resenas` - Muestra esta ayuda\n"
                "• **Permisos:** Gestionar canales\n\n"
            ),
            inline=False
        )
        
        # Información adicional
        embed.add_field(
            name="ℹ️ **Información Importante**",
            value=(
                "• **Configuración:** Los IDs de canales y roles se configuran en el código\n"
                "• **Categoría:** Se crea automáticamente '📚 RESENAS'\n"
                "• **Permisos:** El bot necesita gestionar canales y categorías\n"
                "• **Límites:** Máximo 50 reseñas por sesión\n"
                "• **Estados:** Los usuarios solo pueden tener una reseña activa"
            ),
            inline=False
        )
        
        # Flujo del sistema
        embed.add_field(
            name="🔄 **Flujo del Sistema**",
            value=(
                "1️⃣ Admin ejecuta `!resenas <num>`\n"
                "2️⃣ Se publica mensaje con botón en canal configurado\n"
                "3️⃣ Usuarios hacen clic en 'Quiero reseñas'\n"
                "4️⃣ Se crea canal individual con instrucciones\n"
                "5️⃣ Staff reclama la reseña con botón 'Reclamar'\n"
                "6️⃣ Usuario completa reseña y usa 'Llamar'\n"
                "7️⃣ Staff verifica y usa 'Terminar' para cerrar"
            ),
            inline=False
        )
        
        embed.set_footer(
            text=f"Solicitado por {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)

    # También agregar el manejo de errores para este comando
    @help_resenas.error
    async def help_resenas_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="Necesitas permisos de 'Gestionar canales' para ver la ayuda del sistema de reseñas.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    @commands.command(name="resenas")
    @commands.has_permissions(administrator=True)
    async def comando_resenas(self, ctx, num_resenas: int):
        """
        Comando para administradores que inicia el sistema de reseñas
        
        Uso: !resenas <número>
        Ejemplo: !resenas 3
        """
        
        if num_resenas <= 0:
            embed_error = discord.Embed(
                title="❌ Número inválido",
                description="El número de reseñas debe ser mayor a 0.",
                color=0xff0000
            )
            await ctx.send(embed=embed_error)
            return
        
        if num_resenas > 50:
            embed_error = discord.Embed(
                title="❌ Número muy alto",
                description="Por seguridad, el máximo de reseñas es 50.",
                color=0xff0000
            )
            await ctx.send(embed=embed_error)
            return
        
        canal_resenas = self.bot.get_channel(self.CANAL_RESENAS_ID)
        if not canal_resenas:
            embed_error = discord.Embed(
                title="❌ Canal no encontrado",
                description=f"No se pudo encontrar el canal con ID: {self.CANAL_RESENAS_ID}\n"
                           "Verifica que el ID sea correcto y que el bot tenga acceso.",
                color=0xff0000
            )
            await ctx.send(embed=embed_error)
            return
        
        roles_validos = []
        for role_id in self.STAFF_ROLE_IDS:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_validos.append(role)
        
        embed_confirmacion = discord.Embed(
            title="✅ Sistema de reseñas iniciado",
            description=f"Se han configurado **{num_resenas}** reseñas disponibles.",
            color=0x00ff00
        )
        embed_confirmacion.add_field(
            name="Canal de publicación", 
            value=canal_resenas.mention, 
            inline=True
        )
        
        if roles_validos:
            roles_texto = ", ".join([role.mention for role in roles_validos])
            embed_confirmacion.add_field(
                name="Roles de staff", 
                value=roles_texto, 
                inline=True
            )
        else:
            embed_confirmacion.add_field(
                name="⚠️ Roles de staff", 
                value="No se encontraron roles válidos", 
                inline=True
            )
        
        await ctx.send(embed=embed_confirmacion)
        
        embed_publico = discord.Embed(
            title="📝 Sistema de Reseñas",
            description=f"Hay **{num_resenas}** reseñas disponibles de **{num_resenas}** totales.",
            color=0x0099ff
        )
        embed_publico.add_field(
            name="Estado", 
            value="✅ Disponible", 
            inline=True
        )
        embed_publico.add_field(
            name="Instrucciones", 
            value="Presiona el botón para solicitar una reseña", 
            inline=True
        )
        
        rol_notificacion = ctx.guild.get_role(self.ROL_NOTIFICACION_RESENAS_ID)
        mensaje_notificacion = ""
        if rol_notificacion:
            mensaje_notificacion = rol_notificacion.mention

        mensaje_publico = await canal_resenas.send(mensaje_notificacion, embed=embed_publico)
        
        vista_resenas = ResenasView(num_resenas, self.CANAL_RESENAS_ID, self.STAFF_ROLE_IDS, mensaje_publico.id)
        self.vistas_activas[canal_resenas.id] = vista_resenas
        
        await mensaje_publico.edit(embed=embed_publico, view=vista_resenas)
    
    @commands.command(name="estado_resenas")
    @commands.has_permissions(administrator=True)
    async def estado_resenas(self, ctx):
        """Muestra el estado actual del sistema de reseñas"""
        if not self.vistas_activas:
            embed = discord.Embed(
                title="📊 Estado del Sistema",
                description="No hay sesiones de reseñas activas.",
                color=0x999999
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Estado del Sistema de Reseñas",
            color=0x0099ff
        )
        
        for canal_id, vista in self.vistas_activas.items():
            canal = self.bot.get_channel(canal_id)
            canal_nombre = canal.name if canal else f"Canal {canal_id}"
            
            embed.add_field(
                name=f"#{canal_nombre}",
                value=f"**Disponibles:** {vista.resenas_disponibles}/{vista.resenas_originales}\n"
                      f"**Usuarios activos:** {len(vista.usuarios_con_resena)}\n"
                      f"**Mensaje ID:** {vista.mensaje_id}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="cerrar_resena")
    @commands.has_permissions(manage_channels=True)
    async def cerrar_resena(self, ctx, usuario: discord.Member = None):
        """Cierra el canal de reseña de un usuario y lo libera del sistema"""
        canal_actual = ctx.channel
        
        if not usuario and canal_actual.name.startswith("resenas-"):
            nombre_usuario = canal_actual.name.replace("resenas-", "")
            for member in ctx.guild.members:
                if member.name.lower() == nombre_usuario.lower():
                    usuario = member
                    break
        
        if not usuario:
            embed_error = discord.Embed(
                title="❌ Usuario no especificado",
                description="Debes mencionar al usuario o usar el comando en su canal de reseña.",
                color=0xff0000
            )
            await ctx.send(embed=embed_error)
            return
        
        usuario_liberado = False
        for vista in self.vistas_activas.values():
            if usuario.id in vista.usuarios_con_resena:
                vista.usuarios_con_resena.remove(usuario.id)
                usuario_liberado = True
                
                class FakeInteraction:
                    def __init__(self, guild):
                        self.guild = guild
                
                fake_interaction = FakeInteraction(ctx.guild)
                await vista.actualizar_mensaje_original(fake_interaction)
        
        if canal_actual.name.startswith("resenas-"):
            embed_cierre = discord.Embed(
                title="✅ Reseña completada",
                description=f"La reseña de {usuario.display_name} ha sido completada.",
                color=0x00ff00
            )
            await ctx.send(embed=embed_cierre)
            
            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=3))
            await canal_actual.delete(reason=f"Reseña completada para {usuario.display_name}")
        else:
            if usuario_liberado:
                embed = discord.Embed(
                    title="✅ Usuario liberado",
                    description=f"{usuario.display_name} ha sido liberado del sistema de reseñas.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Usuario no encontrado",
                    description=f"{usuario.display_name} no tenía reseñas activas.",
                    color=0xff9900
                )
            await ctx.send(embed=embed)
    
    @commands.command(name="reset_resenas")
    @commands.has_permissions(administrator=True)
    async def reset_resenas(self, ctx):
        """Resetea el sistema de reseñas, eliminando todas las vistas activas"""
        self.vistas_activas.clear()
        
        embed = discord.Embed(
            title="🔄 Sistema reiniciado",
            description="Se han eliminado todas las sesiones de reseñas activas.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="actualizar_resenas")
    @commands.has_permissions(administrator=True)
    async def actualizar_resenas(self, ctx):
        """Fuerza la actualización de todos los mensajes de reseñas activos"""
        if not self.vistas_activas:
            embed = discord.Embed(
                title="⚠️ Sin sistemas activos",
                description="No hay sistemas de reseñas activos para actualizar.",
                color=0xff9900
            )
            await ctx.send(embed=embed)
            return
        
        actualizados = 0
        for vista in self.vistas_activas.values():
            try:
                class FakeInteraction:
                    def __init__(self, guild):
                        self.guild = guild
                
                fake_interaction = FakeInteraction(ctx.guild)
                await vista.actualizar_mensaje_original(fake_interaction)
                actualizados += 1
            except Exception as e:
                print(f"Error actualizando vista: {e}")
        
        embed = discord.Embed(
            title="🔄 Actualización completada",
            description=f"Se actualizaron {actualizados} mensajes de reseñas.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="config_info")
    @commands.has_permissions(administrator=True)
    async def config_info(self, ctx):
        """Muestra la configuración actual del sistema"""
        embed = discord.Embed(
            title="⚙️ Configuración del Sistema",
            color=0x0099ff
        )
        
        canal = self.bot.get_channel(self.CANAL_RESENAS_ID)
        embed.add_field(
            name="Canal de reseñas",
            value=f"{canal.mention if canal else 'No encontrado'} (ID: {self.CANAL_RESENAS_ID})",
            inline=False
        )
        
        roles_info = []
        for role_id in self.STAFF_ROLE_IDS:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_info.append(f"{role.mention} (ID: {role_id})")
            else:
                roles_info.append(f"Rol no encontrado (ID: {role_id})")
        
        embed.add_field(
            name="Roles de staff",
            value="\n".join(roles_info) if roles_info else "No configurados",
            inline=False
        )
        
        # Estado del sistema
        embed.add_field(
            name="Sistemas activos",
            value=str(len(self.vistas_activas)),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    # Comando de prueba mantenido
    @commands.command(name="resenas_test")
    @commands.has_permissions(administrator=True)
    async def resenas_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Resenas funcionando",
            description="El módulo de economía con sistema de reseñas está cargado correctamente.",
            color=0x00ff00
        )
        embed.add_field(
            name="Comandos disponibles",
            value="`!resenas <num>` - Iniciar sistema de reseñas\n"
                  "`!estado_resenas` - Ver estado actual\n"
                  "`!cerrar_resena @usuario` - Cerrar reseña\n"
                  "`!reset_resenas` - Reiniciar sistema\n"
                  "`!actualizar_resenas` - Forzar actualización\n"
                  "`!config_info` - Ver configuración actual",
            inline=False
        )
        await ctx.send(embed=embed)
    
    # Manejo de errores
    @comando_resenas.error
    async def resenas_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Argumento faltante",
                description="Uso correcto: `!resenas <número>`\nEjemplo: `!resenas 3`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Argumento inválido",
                description="El número de reseñas debe ser un número entero válido.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los administradores pueden usar este comando.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Resenas(bot))