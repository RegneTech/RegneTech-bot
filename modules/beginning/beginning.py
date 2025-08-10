import discord
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuración de canales (puedes modificar estos IDs según tu servidor)
        self.VERIFICATION_CHANNEL_ID = 1400106792821981245
        self.RULES_CHANNEL_ID = 1400106792821981246
        self.FUNCIONAMIENTO_CHANNEL_ID = 1400106793551663187
        self.AUTOROLES_CHANNEL_ID = 1403015632844488839
        self.VERIFIED_ROLE_ID = 1400106792196898888
        self.RESENADOR_ROLE_ID = 1400106792196898891
        self.BUMPEADOR_ROLE_ID = 1400106792196898892

    async def clear_channel(self, channel):
        """Limpia todos los mensajes del canal"""
        try:
            deleted = await channel.purge()
            return len(deleted)
        except discord.Forbidden:
            return 0
        except Exception:
            return 0

    @commands.command(name="help_embeds")
    @commands.has_permissions(administrator=True)
    async def help_embeds(self, ctx):
        """Muestra todos los comandos disponibles del sistema"""
        embed = discord.Embed(
            title="🛠️ Sistema de Setup - Comandos Disponibles",
            description="Lista de todos los comandos disponibles para configurar el servidor:",
            color=0x3498db
        )
        
        embed.add_field(
            name="🔧 Comandos Individuales",
            value="• `!verify_setup` - Configura solo el sistema de verificación\n"
                  "• `!rules_setup` - Envía solo las reglas del servidor\n"
                  "• `!funcionamiento_setup` - Configura solo el funcionamiento de la tienda\n"
                  "• `!autoroles_setup` - Configura solo el sistema de autoroles",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Comando Unificado",
            value="• `!setup_all` - Configura TODOS los sistemas de una vez\n"
                  "  *(Limpia los canales y configura todo automáticamente)*",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Información",
            value="• `!help_embeds` - Muestra esta ayuda\n\n"
                  "**Nota:** Todos los comandos requieren permisos de administrador.",
            inline=False
        )
        
        embed.add_field(
            name="📋 Canales Configurados",
            value=f"• Verificación: <#{self.VERIFICATION_CHANNEL_ID}>\n"
                  f"• Reglas: <#{self.RULES_CHANNEL_ID}>\n"
                  f"• Funcionamiento: <#{self.FUNCIONAMIENTO_CHANNEL_ID}>\n"
                  f"• Autoroles: <#{self.AUTOROLES_CHANNEL_ID}>",
            inline=False
        )
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        embed.set_footer(
            text=f"Sistema de {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="setup_all")
    @commands.has_permissions(administrator=True)
    async def setup_all(self, ctx):
        """Configura todos los sistemas de una vez, limpiando los canales primero"""
        loading_msg = await ctx.send("🔄 Configurando todos los sistemas...")
        
        results = []
        
        # Configurar verificación
        try:
            await self.setup_verification()
            results.append("✅ Sistema de verificación configurado")
        except Exception as e:
            results.append(f"❌ Error en verificación: {str(e)[:50]}")
        
        # Configurar reglas
        try:
            await self.setup_rules(ctx.guild)
            results.append("✅ Reglas del servidor configuradas")
        except Exception as e:
            results.append(f"❌ Error en reglas: {str(e)[:50]}")
        
        # Configurar funcionamiento
        try:
            await self.setup_funcionamiento(ctx.guild)
            results.append("✅ Funcionamiento de tienda configurado")
        except Exception as e:
            results.append(f"❌ Error en funcionamiento: {str(e)[:50]}")
        
        # Configurar autoroles
        try:
            await self.setup_autoroles(ctx.guild)
            results.append("✅ Sistema de autoroles configurado")
        except Exception as e:
            results.append(f"❌ Error en autoroles: {str(e)[:50]}")
        
        # Crear embed de resultados
        embed = discord.Embed(
            title="🎉 Configuración Completa",
            description="Resultado de la configuración de todos los sistemas:",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 Resultados",
            value="\n".join(results),
            inline=False
        )
        
        embed.set_footer(text="Todos los sistemas han sido procesados")
        
        await loading_msg.edit(content="", embed=embed)

    async def setup_verification(self):
        """Configura el sistema de verificación"""
        channel = self.bot.get_channel(self.VERIFICATION_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de verificación no encontrado")
        
        # Limpiar canal
        await self.clear_channel(channel)
        
        # Crear embed
        embed = discord.Embed(
            title="🔐 Verificación del Servidor",
            description="¡Bienvenido a nuestro servidor!\n\n"
                       "Para acceder a todos los canales y participar en la comunidad, "
                       "necesitas verificarte primero.\n\n"
                       "**Haz clic en el botón de abajo para completar tu verificación** ⬇️",
            color=0x2b2d31
        )
        
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        
        embed.add_field(
            name="📋 ¿Por qué verificarse?", 
            value="• Acceso completo al servidor\n• Participar en conversaciones\n• Unirte a eventos y actividades", 
            inline=False
        )
        
        embed.set_footer(
            text=f"Servidor: {channel.guild.name} | Miembros: {channel.guild.member_count}",
            icon_url=channel.guild.icon.url if channel.guild.icon else None
        )
        
        view = VerificationView(self.VERIFIED_ROLE_ID, self.RULES_CHANNEL_ID)
        await channel.send(embed=embed, view=view)

    async def setup_rules(self, guild):
        """Configura las reglas del servidor"""
        channel = self.bot.get_channel(self.RULES_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de reglas no encontrado")
        
        # Limpiar canal
        await self.clear_channel(channel)
        
        embed = discord.Embed(
            title="📜 Reglas del Servidor",
            description="¡Bienvenido/a! Este servidor te permite **ganar dinero, comprar productos y disfrutar de múltiples beneficios**. Para mantener un entorno seguro, justo y divertido para todos, es esencial respetar las siguientes normas:",
            color=0xe74c3c
        )
        
        embed.add_field(
            name="1. 🤝 Respeto ante todo",
            value="No se permite acoso, insultos, discriminación ni conductas tóxicas. Mantén un ambiente cordial y sano.",
            inline=False
        )
        
        embed.add_field(
            name="2. 🚫 Estafas terminantemente prohibidas",
            value="Cualquier intento de engañar, estafar o romper acuerdos será sancionado sin excepción.",
            inline=False
        )
        
        embed.add_field(
            name="3. 💼 Comercio con responsabilidad",
            value="Utiliza únicamente los canales habilitados para comprar o vender. Todo producto ofrecido debe ser legítimo. El servidor **no se hace responsable** por tratos fuera de los canales oficiales.",
            inline=False
        )
        
        embed.add_field(
            name="4. 💸 Sistema económico",
            value="No está permitido abusar del sistema, explotar errores o buscar ventajas injustas. Las recompensas pueden cambiar sin previo aviso según las decisiones del staff.",
            inline=False
        )
        
        embed.add_field(
            name="5. 📢 Sin spam ni publicidad externa",
            value="Está prohibido hacer spam, flood o promocionar servidores/productos sin autorización previa.",
            inline=False
        )
        
        embed.add_field(
            name="6. 🧠 Sentido común y respeto al staff",
            value="No suplantes al staff ni desafíes su autoridad. Ante dudas o problemas, repórtalo por los canales correspondientes.",
            inline=False
        )
        
        embed.add_field(
            name="🚨 Importante",
            value="El incumplimiento de estas normas puede resultar en **sanciones graves o permanentes**.\nAl permanecer en este servidor, **aceptas estas reglas**.",
            inline=False
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(
            text=f"Reglas del servidor {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        await channel.send(embed=embed)

    async def setup_funcionamiento(self, guild):
        """Configura el funcionamiento de la tienda"""
        channel = self.bot.get_channel(self.FUNCIONAMIENTO_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de funcionamiento no encontrado")
        
        # Limpiar canal
        await self.clear_channel(channel)
        
        embed = discord.Embed(
            title="🛒 Funcionamiento de la Tienda",
            description="**Canal oficial:** <#1400106793551663189>\n\n"
                       "La tienda es el lugar donde puedes gastar el dinero que ganes dentro del servidor en objetos exclusivos, retiros, cuentas premium y más. A continuación, te explicamos cómo funciona:",
            color=0x3498db
        )
        
        embed.add_field(
            name="🎁 ¿Qué puedes comprar?",
            value="・**🎟️ Accesos a eventos especiales** Participa en dinámicas únicas desbloqueando objetos de entrada o participación.\n"
                  "・**💸 Retiros de dinero real** Canjea tu saldo acumulado por dinero real si cumples con los requisitos.\n"
                  "・**🧰 Ítems de uso personal** Cuentas premium como HBO, Spotify, Crunchyroll, entre otras. Solo tú podrás usarlas.\n"
                  "・**🎨 Cosméticos de perfil** Personaliza tu cuenta con marcos, insignias, colores, íconos y estilos únicos.\n"
                  "・**⏳ Objetos limitados** Artículos disponibles solo por tiempo limitado o en eventos específicos.",
            inline=False
        )
        
        embed.add_field(
            name="💰 ¿Cómo ganar dinero?",
            value="Por ahora, la única forma de generar ingresos es a través de **reseñas**. **Canal:** <#1400106793551663190>\n\n"
                  "• Cuando estén disponibles, se anunciará allí mismo.\n"
                  "• Solo sigue las instrucciones y completa la reseña correctamente.\n"
                  "• Al hacerlo, recibirás una **recompensa en dinero real** acreditada a tu cuenta.",
            inline=False
        )
        
        embed.add_field(
            name="📌 Consejo",
            value=f"Ve a <#{self.AUTOROLES_CHANNEL_ID}> y ponte el rol <@&{self.RESENADOR_ROLE_ID}> para recibir notificaciones cada vez que una reseña esté disponible.",
            inline=False
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(
            text=f"Funcionamiento de economía {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        await channel.send(embed=embed)

    async def setup_autoroles(self, guild):
        """Configura el sistema de autoroles"""
        channel = self.bot.get_channel(self.AUTOROLES_CHANNEL_ID)
        if not channel:
            raise Exception("Canal de autoroles no encontrado")
        
        # Limpiar canal
        await self.clear_channel(channel)
        
        embed = discord.Embed(
            title="🎭 Sistema de Autoroles",
            description="¡Personaliza tu experiencia en el servidor! Selecciona los roles que más te interesen para recibir notificaciones específicas y acceder a funciones exclusivas.\n\n"
                       "**Haz clic en los botones de abajo para obtener o quitar tus roles:**",
            color=0x7F8C8D
        )
        
        embed.add_field(
            name="【📚 𝚁𝙴𝚂𝙴𝙽̃𝙰𝙳𝙾𝚁】",
            value="Recibe notificaciones cada vez que haya nuevas reseñas disponibles para completar y ganar dinero real.",
            inline=False
        )
        
        embed.add_field(
            name="【🚀 𝙱𝚄𝙼𝙿𝙴𝙰𝙳𝙾𝚁】", 
            value="Ayuda a hacer crecer el servidor y recibe notificaciones cuando sea momento de hacer bump en el servidor.",
            inline=False
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(
            text=f"Autoroles de {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        view = AutoRolesView(self.RESENADOR_ROLE_ID, self.BUMPEADOR_ROLE_ID)
        await channel.send(embed=embed, view=view)

    # Comandos individuales
    @commands.command(name="verify_setup")
    @commands.has_permissions(administrator=True)
    async def verify_setup(self, ctx):
        """Configura el sistema de verificación"""
        try:
            await self.setup_verification()
            await ctx.send(f"✅ Sistema de verificación configurado en <#{self.VERIFICATION_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error al configurar verificación: {str(e)}")

    @commands.command(name="rules_setup")
    @commands.has_permissions(administrator=True)
    async def rules_setup(self, ctx):
        """Envía las reglas del servidor al canal correspondiente"""
        try:
            await self.setup_rules(ctx.guild)
            await ctx.send(f"✅ Reglas configuradas en <#{self.RULES_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error al configurar reglas: {str(e)}")

    @commands.command(name="funcionamiento_setup")
    @commands.has_permissions(administrator=True)
    async def funcionamiento_setup(self, ctx):
        """Envía información sobre el funcionamiento de la tienda"""
        try:
            await self.setup_funcionamiento(ctx.guild)
            await ctx.send(f"✅ Funcionamiento configurado en <#{self.FUNCIONAMIENTO_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error al configurar funcionamiento: {str(e)}")

    @commands.command(name="autoroles_setup")
    @commands.has_permissions(administrator=True)
    async def autoroles_setup(self, ctx):
        """Configura el sistema de autoroles"""
        try:
            await self.setup_autoroles(ctx.guild)
            await ctx.send(f"✅ Autoroles configurados en <#{self.AUTOROLES_CHANNEL_ID}>")
        except Exception as e:
            await ctx.send(f"❌ Error al configurar autoroles: {str(e)}")

class AutoRolesView(discord.ui.View):
    def __init__(self, resenador_role_id, bumpeador_role_id):
        super().__init__(timeout=None)
        self.resenador_role_id = resenador_role_id
        self.bumpeador_role_id = bumpeador_role_id

    @discord.ui.button(label="【📚】", style=discord.ButtonStyle.gray, custom_id="resenador_role")
    async def resenador_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.resenador_role_id)
        
        if not role:
            await interaction.response.send_message(
                "❌ Error: No se pudo encontrar el rol de Reseñador.", 
                ephemeral=True
            )
            return
        
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    f"❌ Te has quitado el rol **{role.name}**. Ya no recibirás notificaciones de reseñas.",
                    ephemeral=True
                )
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    f"✅ ¡Te has asignado el rol **{role.name}**! Ahora recibirás notificaciones cuando haya nuevas reseñas disponibles.",
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Error: No tengo permisos para gestionar este rol.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}", 
                ephemeral=True
            )

    @discord.ui.button(label="【🚀】", style=discord.ButtonStyle.gray, custom_id="bumpeador_role")
    async def bumpeador_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.bumpeador_role_id)
        
        if not role:
            await interaction.response.send_message(
                "❌ Error: No se pudo encontrar el rol de Bumpeador.", 
                ephemeral=True
            )
            return
        
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    f"❌ Te has quitado el rol **{role.name}**. Ya no recibirás notificaciones de bump.",
                    ephemeral=True
                )
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    f"✅ ¡Te has asignado el rol **{role.name}**! Ahora recibirás notificaciones para ayudar con el crecimiento del servidor.",
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Error: No tengo permisos para gestionar este rol.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}", 
                ephemeral=True
            )

class VerificationView(discord.ui.View):
    def __init__(self, verified_role_id, rules_channel_id):
        super().__init__(timeout=None)
        self.verified_role_id = verified_role_id
        self.rules_channel_id = rules_channel_id

    @discord.ui.button(label="🔓 Verificarme", style=discord.ButtonStyle.green, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        verified_role = interaction.guild.get_role(self.verified_role_id)
        
        if not verified_role:
            await interaction.response.send_message(
                "❌ Error: No se pudo encontrar el rol de verificado.", 
                ephemeral=True
            )
            return
        
        if verified_role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ Ya estás verificado.", 
                ephemeral=True
            )
            return
        
        try:
            await interaction.user.add_roles(verified_role)
            
            rules_channel = interaction.guild.get_channel(self.rules_channel_id)
            
            welcome_embed = discord.Embed(
                title="🎉 ¡Verificación completada!",
                description=f"¡Bienvenido oficial a **{interaction.guild.name}**!\n\n"
                           f"✅ Has sido verificado correctamente y ahora tienes acceso completo al servidor.",
                color=0x00ff00
            )
            
            if rules_channel:
                welcome_embed.add_field(
                    name="📋 Próximos pasos",
                    value=f"• Lee nuestras reglas en {rules_channel.mention}\n"
                          f"• Explora los diferentes canales\n"
                          f"• ¡Preséntate con la comunidad!",
                    inline=False
                )
            
            if interaction.guild.icon:
                welcome_embed.set_thumbnail(url=interaction.guild.icon.url)
            
            welcome_embed.set_footer(
                text=f"¡Disfruta tu estancia en {interaction.guild.name}!",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            await interaction.response.send_message(
                embed=welcome_embed,
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Error: No tengo permisos para asignar roles.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}", 
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))