import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone

# Configuración del canal de avisos (cambiar por el ID de tu canal)
AVISOS_CHANNEL_ID = 1400106792821981250

class AvisoModal(discord.ui.Modal, title='📢 Crear Aviso Oficial'):
    def __init__(self):
        super().__init__()

    titulo = discord.ui.TextInput(
        label='📋 Título del Aviso',
        max_length=256,
        required=True
    )
    
    descripcion = discord.ui.TextInput(
        label='📝 Descripción Completa',
        style=discord.TextStyle.paragraph,
        max_length=1800,  # Reducido para dejar espacio al formato
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Obtener el canal de avisos
        channel_id = AVISOS_CHANNEL_ID
        if channel_id is None:
            await interaction.response.send_message(
                "❌ **Error:** No se ha configurado el canal de avisos. "
                "Por favor, configura `AVISOS_CHANNEL_ID` en el código.",
                ephemeral=True
            )
            return
        
        avisos_channel = interaction.guild.get_channel(channel_id)
        if avisos_channel is None:
            await interaction.response.send_message(
                "❌ **Error:** No se pudo encontrar el canal de avisos configurado.",
                ephemeral=True
            )
            return

        # Crear el embed del aviso con mejor estética
        embed = discord.Embed(
            title= f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{self.titulo.value}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            description=f"\n{self.descripcion.value}\n",
            color=0x5865F2,  # Color azul Discord moderno
            timestamp=datetime.now(timezone.utc)
        )
        
        # Agregar línea decorativa y footer del servidor
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False
        )
        
        # Footer con información del servidor
        embed.set_footer(
            text=f"Aviso oficial de {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Thumbnail del servidor
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        try:
            # Crear mensaje con mejor formato
            content = f"@everyone\n\n"
            await avisos_channel.send(content=content, embed=embed)
            
            # Responder al usuario que creó el aviso
            await interaction.response.send_message(
                f"✅ **Aviso publicado exitosamente** en {avisos_channel.mention}\n"
                f"🎯 **Título:** {self.titulo.value}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Error:** No tengo permisos para enviar mensajes en el canal de avisos.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ **Error inesperado:** {str(e)}",
                ephemeral=True
            )

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ────────────────────────────────────────────────────────────
    # Sistema de avisos con formulario modal
    # ────────────────────────────────────────────────────────────
    
    @commands.command(name="aviso")
    @commands.has_permissions(manage_guild=True)
    async def crear_aviso(self, ctx):
        """Abre un formulario para crear un aviso en el canal específico"""
        # Crear y enviar el modal
        modal = AvisoModal()
        
        # Como los comandos de texto no pueden enviar modals directamente,
        # creamos un mensaje con un botón que abre el modal
        class AvisoButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)  # 60 segundos para hacer clic
            
            @discord.ui.button(
                label='Abrir Formulario', 
                style=discord.ButtonStyle.primary, 
                emoji='📝'
            )
            async def crear_aviso_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Verificar que solo el autor del comando pueda usar el botón
                if interaction.user != ctx.author:
                    await interaction.response.send_message(
                        "❌ Solo el autor del comando puede usar este botón.",
                        ephemeral=True
                    )
                    return
                
                await interaction.response.send_modal(AvisoModal())
        
        embed = discord.Embed(
            title="🎯 **Crea un aviso oficial para todo el servidor**",
            description= "• El aviso se enviará con `@everyone`\n"
                       "• Aparecerá con el logo del servidor\n\n"
                       "👇 **Haz clic en el botón para comenzar**",
            color=0x5865F2
        )
        
        # Agregar thumbnail del servidor si existe
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        view = AvisoButton()
        await ctx.send(embed=embed, view=view)

    # ────────────────────────────────────────────────────────────
    # Comandos de moderación básica
    # ────────────────────────────────────────────────────────────
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_member(self, ctx, member: discord.Member, *, reason="No especificada"):
        """Expulsa a un miembro del servidor"""
        if member.top_role >= ctx.author.top_role:
            embed = discord.Embed(
                title="❌ Error",
                description="No puedes expulsar a alguien con un rol igual o superior al tuyo.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            await member.kick(reason=f"Expulsado por {ctx.author} - {reason}")
            embed = discord.Embed(
                title="✅ Usuario expulsado",
                description=f"**{member.display_name}** ha sido expulsado del servidor.",
                color=0x00ff00
            )
            embed.add_field(name="Razón", value=reason, inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para expulsar a este usuario.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_member(self, ctx, member: discord.Member, *, reason="No especificada"):
        """Banea a un miembro del servidor"""
        if member.top_role >= ctx.author.top_role:
            embed = discord.Embed(
                title="❌ Error",
                description="No puedes banear a alguien con un rol igual o superior al tuyo.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            await member.ban(reason=f"Baneado por {ctx.author} - {reason}")
            embed = discord.Embed(
                title="🔨 Usuario baneado",
                description=f"**{member.display_name}** ha sido baneado del servidor.",
                color=0xff0000
            )
            embed.add_field(name="Razón", value=reason, inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para banear a este usuario.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban_member(self, ctx, user_id: int, *, reason="No especificada"):
        """Desbanea a un usuario por su ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Desbaneado por {ctx.author} - {reason}")
            
            embed = discord.Embed(
                title="✅ Usuario desbaneado",
                description=f"**{user.display_name}** ha sido desbaneado del servidor.",
                color=0x00ff00
            )
            embed.add_field(name="Razón", value=reason, inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            await ctx.send(embed=embed)
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ Usuario no encontrado",
                description="No se encontró un usuario con esa ID o no está baneado.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para desbanear usuarios.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────
    # Limpieza de mensajes
    # ────────────────────────────────────────────────────────────
    
    @commands.command(name="clear", aliases=["purge", "clean"])
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: int = 1000):
        """Elimina una cantidad específica de mensajes"""
        if amount < 1 or amount > 10000:
            embed = discord.Embed(
                title="❌ Cantidad inválida",
                description="Debes especificar un número entre 1 y 10000.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 para incluir el comando
            embed = discord.Embed(
                title="🧹 Mensajes eliminados",
                description=f"Se eliminaron **{len(deleted) - 1}** mensajes.",
                color=0x00ff00
            )
            
            # Enviar confirmación y eliminarla después de 5 segundos
            confirmation = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await confirmation.delete()
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Sin permisos",
                description="No tengo permisos para eliminar mensajes.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────
    # Información del servidor
    # ────────────────────────────────────────────────────────────
    
    @commands.command(name="serverinfo")
    @commands.has_permissions(manage_guild=True)
    async def server_info(self, ctx):
        """Muestra información detallada del servidor"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"📊 Información de {guild.name}",
            color=0x00ffff,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        # Información básica
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Propietario", value=guild.owner.mention if guild.owner else "Desconocido", inline=True)
        embed.add_field(name="📅 Creado", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        
        # Estadísticas de miembros
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        bots = sum(1 for member in guild.members if member.bot)
        
        embed.add_field(name="👥 Miembros totales", value=total_members, inline=True)
        embed.add_field(name="🟢 En línea", value=online_members, inline=True)
        embed.add_field(name="🤖 Bots", value=bots, inline=True)
        
        # Canales
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(name="💬 Canales de texto", value=text_channels, inline=True)
        embed.add_field(name="🔊 Canales de voz", value=voice_channels, inline=True)
        embed.add_field(name="📁 Categorías", value=categories, inline=True)
        
        # Roles y emojis
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="😀 Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="🚀 Boost Level", value=guild.premium_tier, inline=True)
        
        await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────
    # Comandos de utilidad
    # ────────────────────────────────────────────────────────────
    
    @commands.command(name="userinfo")
    @commands.has_permissions(manage_guild=True)
    async def user_info(self, ctx, member: discord.Member = None):
        """Muestra información de un usuario"""
        if member is None:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 Información de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else 0x00ffff,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Información básica
        embed.add_field(name="🆔 ID", value=member.id, inline=True)
        embed.add_field(name="📛 Nombre", value=str(member), inline=True)
        embed.add_field(name="📅 Cuenta creada", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        
        # Información del servidor
        embed.add_field(name="📥 Se unió", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🎭 Rol más alto", value=member.top_role.mention, inline=True)
        embed.add_field(name="🤖 Es bot", value="Sí" if member.bot else "No", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say_message(self, ctx, channel: discord.TextChannel, *, message):
        """Hace que el bot envíe un mensaje al canal especificado"""
        try:
            # Verificar que el bot tenga permisos para enviar mensajes en el canal destino
            if not channel.permissions_for(ctx.guild.me).send_messages:
                embed = discord.Embed(
                    title="❌ Sin permisos",
                    description=f"No tengo permisos para enviar mensajes en {channel.mention}.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Enviar el mensaje al canal especificado
            await channel.send(message)
            
            # Confirmar al usuario que el mensaje fue enviado
            embed = discord.Embed(
                title="✅ Mensaje enviado",
                description=f"Mensaje enviado exitosamente a {channel.mention}",
                color=0x00ff00
            )
            await ctx.send(embed=embed, delete_after=5)  # Se elimina después de 5 segundos
            
            # Eliminar el comando original
            await ctx.message.delete()
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Error de permisos",
                description="No tengo permisos suficientes para realizar esta acción.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Ocurrió un error: {str(e)}",
                color=0xff0000
            )
            await ctx.send(embed=embed)

    # ────────────────────────────────────────────────────────────
    # Comando de test para verificar que el módulo funciona
    # ────────────────────────────────────────────────────────────

    @commands.command(name="acomandos")
    @commands.has_permissions(administrator=True)
    async def acomandos(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="Menu de Comandos de Administración",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📋 Comandos disponibles", value=
            "🎉 **Bienvenida** - `!help_welcome`\n"
            "📊 **Niveles** - `!help_levels`\n"
            "🎨 **Embeds** - `!help_embeds`\n"
            "🚀 **Bumps** - `!help_bumps`\n"
            "💰 **Economía** - `!help_economia`\n"
            "⭐ **Reseñas** - `!help_resenas`\n"
            "🔗 **Invitaciones** - `!help_invites`\n"
            "🎫 **Tickets** - `!help_ticket`",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="help_admin")
    @commands.has_permissions(administrator=True)
    async def admin_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Admin funcionando",
            description="El módulo de administración está cargado y funcionando correctamente.",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📋 Comandos disponibles", value=
            "`!kick` - Expulsar usuario\n"
            "`!ban` - Banear usuario\n"
            "`!unban` - Desbanear usuario\n"
            "`!clear` - Limpiar mensajes\n"
            "`!serverinfo` - Info del servidor\n"
            "`!userinfo` - Info de usuario\n"
            "`!say #canal` - Repetir mensaje\n"
            "`!aviso` - Crear aviso con formulario",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[AdminCommands] Módulo de administración listo")

# Función setup requerida para cargar el cog
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))