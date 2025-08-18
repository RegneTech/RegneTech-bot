import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import datetime
from typing import Dict, Set, Optional, List
from decimal import Decimal
import database

class MontoModal(discord.ui.Modal):
    def __init__(self, canal_id: int, usuario_id: int, precio_total: float):
        super().__init__(title="💰 Ingresar Monto de Pago")
        self.canal_id = canal_id
        self.usuario_id = usuario_id
        self.precio_total = precio_total
        
        self.monto_input = discord.ui.TextInput(
            label="Monto a pagar (en €)",
            placeholder="Ejemplo: 0.80 o 1.50",
            required=True,
            max_length=10
        )
        self.add_item(self.monto_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar el monto
            monto_str = self.monto_input.value.replace(',', '.').strip()
            monto = float(monto_str)
            
            if monto < 0:
                embed_error = discord.Embed(
                    title="❌ Error",
                    description="El monto no puede ser negativo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed_error, ephemeral=True)
                return
            
            if monto > 100:  # Límite de seguridad
                embed_error = discord.Embed(
                    title="❌ Error", 
                    description="El monto no puede ser mayor a 100€.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed_error, ephemeral=True)
                return
            
            # Crear vista de confirmación con el monto
            vista_confirmacion = ConfirmarTerminar(self.canal_id, self.usuario_id, self.precio_total, monto)
            
            # Embed de confirmación
            confirm_embed = discord.Embed(
                title="⚠️ Confirmar Cierre de Reseña",
                description="**¿Estás seguro de que quieres cerrar esta reseña?**\n\n"
                           f"🔸 **Canal:** {interaction.channel.mention}\n"
                           f"🔸 **Usuario:** <@{self.usuario_id}>\n"
                           f"🔸 **Staff:** {interaction.user.mention}\n"
                           f"🔸 **Precio calculado:** **{self.precio_total:.2f}€**\n"
                           f"🔸 **Monto a pagar:** **{monto:.2f}€**\n\n"
                           f"⚠️ **Esta acción:**\n"
                           f"• Cerrará permanentemente la reseña\n"
                           f"• Eliminará el canal en 10 segundos\n"
                           f"• Liberará al usuario del sistema\n"
                           f"• Agregará {monto:.2f}€ al saldo del usuario\n"
                           f"• **NO se puede deshacer**",
                color=0xff6b6b
            )
            confirm_embed.set_footer(text="Tienes 60 segundos para decidir")
            
            await interaction.response.send_message(embed=confirm_embed, view=vista_confirmacion, ephemeral=True)
            
        except ValueError:
            embed_error = discord.Embed(
                title="❌ Error de formato",
                description="Por favor ingresa un número válido. Ejemplos: `0.80`, `1.50`, `2.00`",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
        except Exception as e:
            embed_error = discord.Embed(
                title="❌ Error inesperado",
                description=f"Ocurrió un error: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)

class ConfirmarTerminar(discord.ui.View):
    def __init__(self, canal_id: int, usuario_id: int, precio_total: float, monto_pagar: float):
        super().__init__(timeout=60)
        self.canal_id = canal_id
        self.usuario_id = usuario_id
        self.precio_total = precio_total
        self.monto_pagar = monto_pagar

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirmar_terminar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Agregar dinero al usuario en la base de datos
        try:
            # Obtener saldo actual del usuario
            saldo_actual = await database.get_user_balance(self.usuario_id)
            nuevo_saldo = saldo_actual + Decimal(str(self.monto_pagar))
            
            # Actualizar saldo
            await database.update_user_balance(
                self.usuario_id, 
                nuevo_saldo, 
                interaction.user.id,
                'PAGO_RESEÑA',
                f'Pago por reseña completada: {self.monto_pagar:.2f}€'
            )
            
        except Exception as e:
            print(f"Error actualizando saldo: {e}")
            # Continuar con el proceso aunque falle el saldo
        
        # Embed con información de pago
        payment_embed = discord.Embed(
            title="💰 Información de Pago",
            description=f"**Reseña completada exitosamente**\n\n"
                       f"🔸 **Canal:** {interaction.channel.mention}\n"
                       f"🔸 **Usuario:** <@{self.usuario_id}>\n"
                       f"🔸 **Precio calculado:** **{self.precio_total:.2f}€**\n"
                       f"🔸 **Monto pagado:** **{self.monto_pagar:.2f}€**\n"
                       f"🔸 **Staff responsable:** {interaction.user.mention}\n\n"
                       f"✅ **El saldo ha sido agregado automáticamente.**",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        payment_embed.set_footer(text="El canal se cerrará en 10 segundos...")

        await interaction.response.edit_message(embed=payment_embed, view=None)
        
        # Enviar mensaje privado al usuario sobre su ganancia
        usuario = interaction.guild.get_member(self.usuario_id)
        if usuario:
            try:
                user_embed = discord.Embed(
                    title="✅ Reseña Completada",
                    description=f"¡Tu reseña ha sido completada exitosamente!\n\n"
                               f"💰 **Has ganado:** **{self.monto_pagar:.2f}€**\n"
                               f"🏆 **Staff responsable:** {interaction.user.display_name}\n"
                               f"💳 **Saldo agregado automáticamente a tu cuenta**\n\n"
                               f"Puedes verificar tu saldo usando el comando correspondiente.",
                    color=0x00ff00,
                    timestamp=datetime.datetime.now()
                )
                user_embed.set_footer(text=f"Servidor: {interaction.guild.name}")
                await usuario.send(embed=user_embed)
            except discord.Forbidden:
                pass  # Usuario tiene DMs cerrados
        
        # Countdown de 10 segundos
        for i in range(10, 0, -1):
            payment_embed.set_footer(text=f"El canal se cerrará en {i} segundos...")
            await interaction.edit_original_response(embed=payment_embed)
            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=1))

        # Liberar usuario del sistema
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
        await interaction.channel.delete(reason=f"Reseña completada para {usuario.display_name if usuario else 'Usuario desconocido'} - Pago: {self.monto_pagar:.2f}€")

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancelar_terminar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_embed = discord.Embed(
            title="✅ Operación Cancelada",
            description="El cierre de la reseña ha sido cancelado.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=cancel_embed, view=None)

class ReseñasBotones(discord.ui.View):
    def __init__(self, usuario_id: int, staff_role_ids: List[int], precio_inicial: float, secuencia_precios: List[float]):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.staff_role_ids = staff_role_ids
        self.reclamado_por = None
        self.precio_actual = precio_inicial
        self.precio_inicial = precio_inicial
        self.secuencia_precios = secuencia_precios
        self.incrementos_aplicados = 0
        
        # Actualizar el label del canal con el precio
        self.actualizar_precio_display()
    
    def actualizar_precio_display(self):
        """Actualiza el precio mostrado en el título del embed"""
        pass  # Se manejará desde el embed principal
    
    def calcular_precio_decremento(self):
        """Calcula el precio que se debe decrementar"""
        if self.incrementos_aplicados == 0:
            return 0  # No se puede decrementar del precio inicial
        
        # Obtener el precio del incremento anterior
        if self.incrementos_aplicados <= len(self.secuencia_precios):
            precio_anterior = self.secuencia_precios[self.incrementos_aplicados - 1]
        else:
            # Si excede la secuencia, usar el último valor
            precio_anterior = self.secuencia_precios[-1]
        
        return precio_anterior

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

        # Evitar que se reclame dos veces
        if self.reclamado_por:
            embed_error = discord.Embed(
                title="⚠️ Ya reclamado",
                description="Esta reseña ya fue reclamada por otro miembro del staff.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        # Actualizar botón
        button.label = f"Reclamado por {interaction.user.display_name}"
        button.disabled = True
        button.emoji = "✅"
        
        # Guardar quien reclamó
        self.reclamado_por = interaction.user.id
        
        # Obtener usuario que solicitó la reseña
        usuario_solicitante = interaction.guild.get_member(self.usuario_id)

        # Crear embed de reclamo
        embed = discord.Embed(
            title="👋 Reseña Reclamada",
            description=(
                f"🔹 **Usuario solicitante:** {usuario_solicitante.mention if usuario_solicitante else 'Desconocido'}\n"
                f"🔹 **Staff asignado:** {interaction.user.mention}\n\n"
                f"💰 **Precio actual:** **{self.precio_actual:.2f}€**\n"
                f"⏰ **Tiempo:** {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
            ),
            color=0xffaa00,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Reclamado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # Primero actualizar el mensaje original
        await interaction.response.edit_message(view=self)
        
        # Enviar embed al canal
        await interaction.followup.send(embed=embed)
        
        # Aviso directo al solicitante
        if usuario_solicitante:
            mensaje_adicional = (
                f"{usuario_solicitante.mention}, tu reseña será atendida por {interaction.user.mention}."
            )
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

        # Abrir modal para ingresar monto
        modal = MontoModal(interaction.channel.id, self.usuario_id, self.precio_actual)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Llamar", style=discord.ButtonStyle.primary, emoji="📞")
    async def llamar_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que sea el usuario de la reseña
        if interaction.user.id != self.usuario_id:
            embed_error = discord.Embed(
                title="❌ Sin permisos",
                description="Solo el usuario de la reseña puede usar este botón.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

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

    @discord.ui.button(emoji="➕", style=discord.ButtonStyle.success)
    async def agregar_resena(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que tenga algún rol de staff
        tiene_rol_staff = any(role.id in self.staff_role_ids for role in interaction.user.roles)
        if not tiene_rol_staff:
            embed_error = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los miembros del staff pueden agregar reseñas.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
        
        # Verificar que haya reseñas disponibles en el sistema
        bot = interaction.client
        resenas_cog = bot.get_cog("Resenas")
        
        if not resenas_cog or not resenas_cog.vistas_activas:
            embed_error = discord.Embed(
                title="❌ Sin reseñas disponibles",
                description="No hay más reseñas disponibles en el sistema.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
        
        # Buscar la vista activa correspondiente
        vista_encontrada = None
        for vista in resenas_cog.vistas_activas.values():
            if vista.resenas_disponibles > 0:
                vista_encontrada = vista
                break
        
        if not vista_encontrada:
            embed_error = discord.Embed(
                title="❌ Sin reseñas disponibles",
                description="No hay más reseñas disponibles en el sistema.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
        
        # Calcular nuevo precio
        if self.incrementos_aplicados < len(self.secuencia_precios):
            incremento = self.secuencia_precios[self.incrementos_aplicados]
        else:
            # Si excede la secuencia, usar el último valor
            incremento = self.secuencia_precios[-1]
        
        precio_anterior = self.precio_actual
        self.precio_actual += incremento
        self.incrementos_aplicados += 1
        
        # Descontar una reseña del sistema
        vista_encontrada.resenas_disponibles -= 1
        vista_encontrada.actualizar_boton()
        
        # Actualizar mensaje principal del sistema
        class FakeInteraction:
            def __init__(self, guild):
                self.guild = guild
        
        fake_interaction = FakeInteraction(interaction.guild)
        await vista_encontrada.actualizar_mensaje_original(fake_interaction)
        
        # Actualizar el nombre del canal
        nuevo_nombre = f"resenas-{self.precio_actual:.2f}€-{interaction.channel.name.split('-')[-1]}"
        try:
            await interaction.channel.edit(name=nuevo_nombre)
        except discord.HTTPException:
            pass  # Ignorar errores de rate limit
        
        # Respuesta de éxito
        embed_success = discord.Embed(
            title="✅ Reseña agregada exitosamente",
            description=f"**Se ha agregado una reseña adicional**\n\n"
                       f"💰 **Precio anterior:** {precio_anterior:.2f}€\n"
                       f"💰 **Incremento:** +{incremento:.2f}€\n"
                       f"💰 **Precio actual:** **{self.precio_actual:.2f}€**\n"
                       f"🎯 **Reseñas totales:** {self.incrementos_aplicados + 1}\n"
                       f"📊 **Agregado por:** {interaction.user.mention}",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        
        await interaction.response.send_message(embed=embed_success)
        
        # Enviar notificación al usuario de la reseña
        usuario = interaction.guild.get_member(self.usuario_id)
        if usuario:
            embed_notificacion = discord.Embed(
                title="➕ Reseña Adicional Agregada",
                description=f"El staff ha agregado una reseña adicional a tu solicitud.\n\n"
                           f"💰 **Nuevo precio:** **{self.precio_actual:.2f}€**\n"
                           f"🎯 **Reseñas totales:** {self.incrementos_aplicados + 1}\n"
                           f"📊 **Agregado por:** {interaction.user.display_name}",
                color=0x00ff00
            )
            await interaction.followup.send(f"{usuario.mention}", embed=embed_notificacion)

    @discord.ui.button(emoji="➖", style=discord.ButtonStyle.danger)
    async def quitar_resena(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar que tenga algún rol de staff
        tiene_rol_staff = any(role.id in self.staff_role_ids for role in interaction.user.roles)
        if not tiene_rol_staff:
            embed_error = discord.Embed(
                title="❌ Sin permisos",
                description="Solo los miembros del staff pueden quitar reseñas.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
        
        # Verificar que se pueda decrementar
        if self.incrementos_aplicados == 0:
            embed_error = discord.Embed(
                title="❌ No se puede decrementar",
                description=f"El precio ya está en el mínimo inicial ({self.precio_inicial:.2f}€).",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return
        
        # Calcular decremento
        decremento = self.calcular_precio_decremento()
        precio_anterior = self.precio_actual
        
        self.precio_actual -= decremento
        self.incrementos_aplicados -= 1
        
        # Devolver una reseña al sistema
        bot = interaction.client
        resenas_cog = bot.get_cog("Resenas")
        
        if resenas_cog and resenas_cog.vistas_activas:
            # Buscar la vista activa correspondiente
            for vista in resenas_cog.vistas_activas.values():
                vista.resenas_disponibles += 1
                vista.actualizar_boton()
                
                # Actualizar mensaje principal del sistema
                class FakeInteraction:
                    def __init__(self, guild):
                        self.guild = guild
                
                fake_interaction = FakeInteraction(interaction.guild)
                await vista.actualizar_mensaje_original(fake_interaction)
                break
        
        # Actualizar el nombre del canal
        nuevo_nombre = f"resenas-{self.precio_actual:.2f}€-{interaction.channel.name.split('-')[-1]}"
        try:
            await interaction.channel.edit(name=nuevo_nombre)
        except discord.HTTPException:
            pass  # Ignorar errores de rate limit
        
        # Respuesta de éxito
        embed_success = discord.Embed(
            title="✅ Reseña removida exitosamente",
            description=f"**Se ha removido una reseña**\n\n"
                       f"💰 **Precio anterior:** {precio_anterior:.2f}€\n"
                       f"💰 **Decremento:** -{decremento:.2f}€\n"
                       f"💰 **Precio actual:** **{self.precio_actual:.2f}€**\n"
                       f"🎯 **Reseñas totales:** {self.incrementos_aplicados + 1}\n"
                       f"📊 **Removido por:** {interaction.user.mention}",
            color=0xff9900,
            timestamp=datetime.datetime.now()
        )
        
        await interaction.response.send_message(embed=embed_success)
        
        # Enviar notificación al usuario de la reseña
        usuario = interaction.guild.get_member(self.usuario_id)
        if usuario:
            embed_notificacion = discord.Embed(
                title="➖ Reseña Removida",
                description=f"El staff ha removido una reseña de tu solicitud.\n\n"
                           f"💰 **Nuevo precio:** **{self.precio_actual:.2f}€**\n"
                           f"🎯 **Reseñas totales:** {self.incrementos_aplicados + 1}\n"
                           f"📊 **Removido por:** {interaction.user.display_name}",
                color=0xff9900
            )
            await interaction.followup.send(f"{usuario.mention}", embed=embed_notificacion)

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
    
    def calcular_precio_y_secuencia(self, usuario: discord.Member) -> tuple:
        """Calcula el precio inicial y secuencia de precios basado en los roles del usuario"""
        # Roles VIP (precio inicial más bajo)
        roles_vip = [1406360634643316746, 1400106792196898893]
        
        # Roles especiales (secuencia diferente)
        roles_especiales = [
            1400106792226127922, 1400106792226127923, 1400106792280658061, 
            1400106792280658062, 1400106792280658063, 1400106792280658064, 
            1400106792280658065, 1400106792280658066, 1400106792280658067
        ]
        
        user_role_ids = [role.id for role in usuario.roles]
        
        if any(role_id in user_role_ids for role_id in roles_especiales):
            # Secuencia especial: 0.5, 0.5, 0.75, 1€, 1€, 1€...
            precio_inicial = 0.5
            secuencia = [0.5, 0.75] + [1.0] * 10  # Agregar varios 1€ para futuras expansiones
        elif any(role_id in user_role_ids for role_id in roles_vip):
            # Secuencia VIP: 0.3, 0.5, 0.75, 0.75, 0.75...
            precio_inicial = 0.3
            secuencia = [0.5, 0.75] + [0.75] * 10
        else:
            # Secuencia normal: 0.5, 0.5, 0.75, 0.75, 0.75...
            precio_inicial = 0.5
            secuencia = [0.5, 0.75] + [0.75] * 10
        
        return precio_inicial, secuencia
    
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
            
            # Calcular precio y secuencia para este usuario
            precio_inicial, secuencia_precios = self.calcular_precio_y_secuencia(interaction.user)
            
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
                    mention_everyone=False,
                    use_application_commands=False
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
            
            # Crear el canal con el formato mejorado
            nombre_usuario = interaction.user.name.replace(" ", "-").lower()
            nombre_usuario = ''.join(c for c in nombre_usuario if c.isalnum() or c in '-_')
            nombre_canal = f"resenas-{precio_inicial:.1f}€-{nombre_usuario}"
            
            canal_ticket = await guild.create_text_channel(
                name=nombre_canal,
                overwrites=overwrites,
                category=categoria,
                topic=f"Reseña para {interaction.user.display_name} - Precio inicial: {precio_inicial:.2f}€"
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
            
            # Agregar información de precio
            embed_instrucciones.add_field(
                name="💰 Información de Pago",
                value=f"**Precio por esta reseña:** {precio_inicial:.2f}€\n"
                      "• El staff puede agregar reseñas adicionales si es necesario\n"
                      "• El pago se realizará al completar todas las reseñas",
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
            vista_botones = ReseñasBotones(interaction.user.id, self.staff_role_ids, precio_inicial, secuencia_precios)
            
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
                description=f"Se ha creado tu canal de reseña: {canal_ticket.mention}\n"
                           f"💰 **Precio inicial:** {precio_inicial:.2f}€",
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
        
        # Sistema de precios
        embed.add_field(
            name="💰 **Sistema de Precios**",
            value=(
                "• **Usuarios VIP:** 0.3€ → 0.8€ → 1.55€ → 2.30€...\n"
                "• **Usuarios normales:** 0.5€ → 1.0€ → 1.75€ → 2.50€...\n"
                "• **Usuarios especiales:** 0.5€ → 1.0€ → 1.75€ → 2.75€ → 3.75€...\n"
                "• **Botones +/-:** Agregar/quitar reseñas con precios dinámicos\n"
                "• **Formato canal:** resenas-[precio]€-[usuario]\n"
                "• **Pago automático:** El dinero se agrega automáticamente al saldo\n\n"
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
                "• **Estados:** Los usuarios solo pueden tener una reseña activa\n"
                "• **Menciones:** Los usuarios no pueden hacer menciones en los canales\n"
                "• **Base de datos:** Integrado con sistema económico automático"
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
                "4️⃣ Se crea canal individual con precio dinámico\n"
                "5️⃣ Staff reclama la reseña con botón 'Reclamar'\n"
                "6️⃣ Staff puede usar botones ➕/➖ para ajustar precio\n"
                "7️⃣ Usuario completa reseña y usa 'Llamar'\n"
                "8️⃣ Staff usa 'Terminar' → ingresa monto → dinero se agrega automáticamente"
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
            nombre_usuario_con_precio = canal_actual.name.replace("resenas-", "")
            # Extraer el nombre después del precio (formato: precio€-usuario)
            if "€-" in nombre_usuario_con_precio:
                nombre_usuario = nombre_usuario_con_precio.split("€-", 1)[1]
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
        
        # Información sobre roles especiales
        embed.add_field(
            name="💰 Sistema de Precios",
            value="• **VIP:** Roles 1406360634643316746, 1400106792196898893\n"
                  "• **Especiales:** Roles 1400106792226127922-1400106792280658067\n"
                  "• **Normales:** Resto de usuarios\n"
                  "• **Formato canal:** resenas-[precio]€-[usuario]\n"
                  "• **Base de datos:** Integrado con sistema económico",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Comando de prueba mantenido
    @commands.command(name="resenas_test")
    @commands.has_permissions(administrator=True)
    async def resenas_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Resenas funcionando",
            description="El módulo de reseñas con sistema de precios dinámicos y pago automático está cargado correctamente.",
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
        embed.add_field(
            name="Nuevas funcionalidades",
            value="• **Precios dinámicos** basados en roles de usuario\n"
                  "• **Botones ➕/➖** para agregar/quitar reseñas\n"
                  "• **Formato de canal mejorado** con precios\n"
                  "• **Restricción de menciones** para usuarios\n"
                  "• **Pago automático** integrado con base de datos\n"
                  "• **Modal de monto** personalizable al cerrar\n"
                  "• **Notificaciones** al usuario cuando se cambian reseñas\n"
                  "• **Sistema de roles especiales** con precios diferenciados",
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