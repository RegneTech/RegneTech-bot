import discord
from discord.ext import commands
from datetime import datetime, timezone
import random
import aiohttp
from PIL import Image, ImageDraw
import io
import os

# Configuración de canales
WELCOME_CHANNEL_ID = 1400106792821981247  # ID del canal de bienvenida específico
GENERAL_CHANNEL_ID = 1400106792821981253   # ID del canal general

# Configuración de roles
BASE_ROLE_ID = 1400106792196898888  # Rol base que se revisa
AUTO_ROLE_ID = 1406360634643316746  # Rol que se asigna automáticamente
RANGO_PREFIX = "◈ Rango"  # Prefijo de roles de rango

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Lista de mensajes de bienvenida aleatorios
        self.welcome_messages = [
            "Te damos la bienvenida! Esperamos que hayas traído pizza. 🍕",
            "¡Un nuevo aventurero se ha unido a nosotros! 🎉",
            "¡Bienvenido/a! Que comience la diversión. 🎊",
            "¡Genial! Otro miembro increíble se ha unido. ✨",
            "¡Hola! Espero que te sientas como en casa. 🏠",
            "¡Bienvenido/a al mejor servidor de Discord! 🌟",
            "¡Un nuevo amigo ha llegado! ¡Dale la bienvenida! 👋"
        ]
        
        # Ruta de la imagen de fondo específica
        self.background_image = "resources/images/welcome.png"
        self.background_dir = "resources/images"
        
        # Crear directorio si no existe
        os.makedirs(self.background_dir, exist_ok=True)
        
        # ═══ CONFIGURACIÓN DE AVATAR ═══
        # Tamaño del avatar (en píxeles)
        self.avatar_size = 200
        
        # Posición del avatar
        self.avatar_position = "center"  # "center", "top", "bottom", "custom"
        
        # Para posición personalizada
        self.avatar_x_offset = 0  # Desplazamiento horizontal
        self.avatar_y_offset = 0  # Desplazamiento vertical
        
        # Configuración del borde del avatar
        self.avatar_border_size = 0  # Tamaño del borde en píxeles (0 para sin borde)
        self.avatar_border_color = (255, 255, 255, 255)

    # ═══ FUNCIONES DE GESTIÓN DE ROLES ═══
    
    async def check_and_assign_auto_role(self, member):
        """Verifica si el usuario tiene el rol base y le asigna el rol automático si no tiene rol de rango"""
        try:
            base_role = member.guild.get_role(BASE_ROLE_ID)
            auto_role = member.guild.get_role(AUTO_ROLE_ID)
            
            if not base_role or not auto_role:
                print(f"⚠️ Roles no encontrados - Base: {base_role}, Auto: {auto_role}")
                return
            
            # Verificar si tiene el rol base
            if base_role in member.roles:
                # Verificar si NO tiene rol de rango
                has_rango_role = any(role.name.startswith(RANGO_PREFIX) for role in member.roles)
                
                if not has_rango_role and auto_role not in member.roles:
                    await member.add_roles(auto_role, reason="Asignación automática - sin rol de rango")
                    print(f"✅ Rol automático asignado a {member.display_name}")
                    
        except Exception as e:
            print(f"❌ Error asignando rol automático a {member.display_name}: {e}")

    async def check_and_remove_auto_role(self, member, after_roles):
        """Verifica si se añadió un rol de rango y remueve el rol automático"""
        try:
            base_role = member.guild.get_role(BASE_ROLE_ID)
            auto_role = member.guild.get_role(AUTO_ROLE_ID)
            
            if not base_role or not auto_role:
                return
            
            # Verificar si tiene el rol base
            if base_role in member.roles:
                # Verificar si tiene rol de rango en los roles actuales
                has_rango_role = any(role.name.startswith(RANGO_PREFIX) for role in after_roles)
                
                if has_rango_role and auto_role in member.roles:
                    await member.remove_roles(auto_role, reason="Removido automáticamente - usuario tiene rol de rango")
                    print(f"✅ Rol automático removido de {member.display_name} (tiene rol de rango)")
                    
        except Exception as e:
            print(f"❌ Error removiendo rol automático de {member.display_name}: {e}")

    async def bulk_check_auto_roles(self, guild):
        """Revisa todos los miembros del servidor para aplicar las reglas de roles"""
        try:
            base_role = guild.get_role(BASE_ROLE_ID)
            auto_role = guild.get_role(AUTO_ROLE_ID)
            
            if not base_role or not auto_role:
                print("⚠️ Roles no encontrados para revisión masiva")
                return
            
            members_with_base_role = [member for member in guild.members if base_role in member.roles]
            print(f"🔍 Revisando {len(members_with_base_role)} miembros con rol base...")
            
            for member in members_with_base_role:
                has_rango_role = any(role.name.startswith(RANGO_PREFIX) for role in member.roles)
                
                if has_rango_role and auto_role in member.roles:
                    # Remover rol automático si tiene rol de rango
                    await member.remove_roles(auto_role, reason="Revisión masiva - tiene rol de rango")
                    print(f"📤 Removido rol automático de {member.display_name}")
                    
                elif not has_rango_role and auto_role not in member.roles:
                    # Añadir rol automático si no tiene rol de rango
                    await member.add_roles(auto_role, reason="Revisión masiva - sin rol de rango")
                    print(f"📥 Asignado rol automático a {member.display_name}")
                    
        except Exception as e:
            print(f"❌ Error en revisión masiva de roles: {e}")

    # ═══ EVENTOS DE DISCORD ═══
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Evento que se ejecuta cuando un nuevo miembro se une al servidor"""
        await self.send_welcome_message(member)
        await self.send_general_welcome(member)
        # Verificar y asignar rol automático después de un breve delay
        await asyncio.sleep(1)
        await self.check_and_assign_auto_role(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Evento que se ejecuta cuando se actualizan los roles de un miembro"""
        # Verificar si se añadieron roles
        if before.roles != after.roles:
            # Verificar si se añadió un rol de rango
            new_roles = set(after.roles) - set(before.roles)
            rango_role_added = any(role.name.startswith(RANGO_PREFIX) for role in new_roles)
            
            if rango_role_added:
                await self.check_and_remove_auto_role(after, after.roles)
            else:
                # Si se removieron roles, verificar si necesita el rol automático
                removed_roles = set(before.roles) - set(after.roles)
                rango_role_removed = any(role.name.startswith(RANGO_PREFIX) for role in removed_roles)
                
                if rango_role_removed:
                    await self.check_and_assign_auto_role(after)

    # ═══ FUNCIONES DE IMAGEN ═══

    async def download_avatar(self, user):
        """Descarga el avatar del usuario"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(user.display_avatar.url)) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
        except Exception as e:
            print(f"❌ Error descargando avatar: {e}")
            return None

    def create_circular_avatar(self, avatar_bytes, size=None):
        """Crea un avatar circular con borde configurable"""
        if size is None:
            size = self.avatar_size
            
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes))
            avatar = avatar.convert("RGBA")
            avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
            
            # Crear máscara circular
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            
            # Crear imagen circular
            output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            output.paste(avatar, (0, 0))
            output.putalpha(mask)
            
            # Agregar borde si está configurado
            if self.avatar_border_size > 0:
                border_size = self.avatar_border_size
                bordered_size = size + (border_size * 2)
                bordered = Image.new("RGBA", (bordered_size, bordered_size), (0, 0, 0, 0))
                
                # Dibujar círculo de borde
                draw_border = ImageDraw.Draw(bordered)
                draw_border.ellipse([0, 0, bordered_size-1, bordered_size-1], 
                                  fill=self.avatar_border_color, outline=self.avatar_border_color)
                
                # Pegar avatar encima del borde
                bordered.paste(output, (border_size, border_size), output)
                return bordered
            
            return output
            
        except Exception as e:
            print(f"❌ Error creando avatar circular: {e}")
            return None

    def calculate_avatar_position(self, bg_width, bg_height, avatar_width, avatar_height):
        """Calcula la posición del avatar según la configuración"""
        if self.avatar_position == "center":
            x = (bg_width - avatar_width) // 2
            y = (bg_height - avatar_height) // 2
        elif self.avatar_position == "top":
            x = (bg_width - avatar_width) // 2
            y = avatar_height // 2
        elif self.avatar_position == "bottom":
            x = (bg_width - avatar_width) // 2
            y = bg_height - avatar_height - (avatar_height // 2)
        elif self.avatar_position == "custom":
            center_x = (bg_width - avatar_width) // 2
            center_y = (bg_height - avatar_height) // 2
            x = center_x + self.avatar_x_offset
            y = center_y + self.avatar_y_offset
        else:
            x = (bg_width - avatar_width) // 2
            y = (bg_height - avatar_height) // 2
        
        # Asegurar que el avatar no se salga de la imagen
        x = max(0, min(x, bg_width - avatar_width))
        y = max(0, min(y, bg_height - avatar_height))
        
        return x, y

    async def create_welcome_image(self, member):
        """Crea una imagen de bienvenida con avatar superpuesto"""
        try:
            # Verificar que existe la imagen de fondo
            if not os.path.exists(self.background_image):
                print(f"⚠️ Imagen de fondo no encontrada: {self.background_image}")
                return None
            
            # Cargar imagen de fondo
            background = Image.open(self.background_image).convert("RGBA")
            
            # Redimensionar fondo si es muy grande
            bg_width, bg_height = background.size
            if bg_width > 1000:
                ratio = 1000 / bg_width
                new_height = int(bg_height * ratio)
                background = background.resize((1000, new_height), Image.Resampling.LANCZOS)
                bg_width, bg_height = background.size
            
            # Descargar avatar del usuario
            avatar_bytes = await self.download_avatar(member)
            if not avatar_bytes:
                print(f"⚠️ No se pudo descargar el avatar de {member.display_name}")
                return None
            
            # Crear avatar circular con tamaño configurado
            avatar_size = self.avatar_size
            avatar = self.create_circular_avatar(avatar_bytes, size=avatar_size)
            
            if not avatar:
                return None
            
            # Calcular posición del avatar
            avatar_x, avatar_y = self.calculate_avatar_position(bg_width, bg_height, avatar.width, avatar.height)
            
            # Pegar avatar en la posición calculada
            background.paste(avatar, (avatar_x, avatar_y), avatar)
            
            # Convertir a bytes para enviar
            img_bytes = io.BytesIO()
            background.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            print(f"❌ Error creando imagen de bienvenida: {e}")
            return None

    async def create_join_visual(self, member):
        """Crea imagen usando welcome-general.png como base y añade avatares circulares"""
        try:
            # Cargar imagen base
            base_image_path = "resources/images/welcome-general.png"
            
            try:
                img = Image.open(base_image_path).convert("RGBA")
            except FileNotFoundError:
                print(f"❌ No se encontró la imagen base: {base_image_path}")
                return None
            
            # Obtener dimensiones de la imagen base
            width, height = img.size
            
            # Descargar avatar del usuario que se une
            user_avatar_bytes = await self.download_avatar(member)
            
            # Descargar logo del servidor
            server_avatar_bytes = None
            if member.guild.icon:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(member.guild.icon.url)) as response:
                        if response.status == 200:
                            server_avatar_bytes = await response.read()
            
            # Tamaño de los avatares circulares
            avatar_size = 65  # Ajusta según el tamaño de tu imagen base
            
            # Posiciones (ajusta según tu imagen)
            # Usuario a la derecha
            user_x = width - avatar_size - 540
            user_y = (height - avatar_size) // 2 + 15
            
            # Servidor a la izquierda  
            server_x = 543
            server_y = (height - avatar_size) // 2 - 50
            
            # Función para hacer imagen circular
            def make_circular(image, size):
                # Redimensionar
                image = image.resize((size, size), Image.Resampling.LANCZOS)
                
                # Crear máscara circular
                mask = Image.new("L", (size, size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, size, size), fill=255)
                
                # Aplicar máscara
                image.putalpha(mask)
                return image
            
            # Agregar avatar del usuario (derecha)
            if user_avatar_bytes:
                user_avatar = Image.open(io.BytesIO(user_avatar_bytes)).convert("RGBA")
                user_avatar_circular = make_circular(user_avatar, avatar_size)
                img.paste(user_avatar_circular, (user_x, user_y), user_avatar_circular)
            
            # Agregar logo del servidor (izquierda)
            if server_avatar_bytes:
                server_avatar = Image.open(io.BytesIO(server_avatar_bytes)).convert("RGBA")
                server_avatar_circular = make_circular(server_avatar, avatar_size)
                img.paste(server_avatar_circular, (server_x, server_y), server_avatar_circular)
            
            # Convertir a bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            print(f"❌ Error creando visual: {e}")
            return None

    # ═══ FUNCIONES DE MENSAJES ═══

    async def send_welcome_message(self, member):
        """Envía mensaje de bienvenida con imagen personalizada"""
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            print(f"❌ Canal de bienvenida {WELCOME_CHANNEL_ID} no encontrado")
            return
        
        # Seleccionar mensaje aleatorio
        welcome_text = random.choice(self.welcome_messages)
        
        # Crear imagen personalizada con avatar superpuesto
        welcome_image = await self.create_welcome_image(member)
        
        embed = discord.Embed(
            title=f"¡Bienvenido/a {member.display_name}! 🎉",
            description=welcome_text,
            color=0x00ffff,
            timestamp=datetime.now(timezone.utc)
        )
        
        try:
            if welcome_image:
                # Enviar imagen personalizada con avatar superpuesto
                file = discord.File(welcome_image, filename="welcome.png")
                embed.set_image(url="attachment://welcome.png")
                await channel.send(embed=embed, file=file)
                print(f"✅ Bienvenida con imagen personalizada enviada para {member.display_name}")
            else:
                # Fallback: imagen de fondo sin avatar superpuesto
                if os.path.exists(self.background_image):
                    with open(self.background_image, 'rb') as f:
                        file = discord.File(f, filename="welcome_bg.png")
                        embed.set_image(url="attachment://welcome_bg.png")
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed, file=file)
                        print(f"✅ Bienvenida básica enviada para {member.display_name}")
                else:
                    # Último fallback: solo avatar
                    embed.set_image(url=member.display_avatar.url)
                    await channel.send(embed=embed)
                    print(f"✅ Bienvenida simple enviada para {member.display_name}")
            
        except Exception as e:
            print(f"❌ Error enviando mensaje de bienvenida: {e}")
            # Último fallback silencioso
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    async def send_general_welcome(self, member):
        """Envía mensaje de bienvenida con imagen personalizada"""
        channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print(f"❌ Canal general {GENERAL_CHANNEL_ID} no encontrado")
            return
        
        # Crear imagen visual
        join_visual = await self.create_join_visual(member)
        
        # Crear embed
        embed = discord.Embed(
        description=f"{member.mention} ha llegado al reino, brindémosle una gran bienvenida! 🎉",
        color=0x7289da
        )

        # Enviar embed con imagen
        if join_visual:
            file = discord.File(join_visual, filename="welcome.png")
            embed.set_image(url="attachment://welcome.png")
            await channel.send(embed=embed, file=file)
        else:
            # Fallback si no se puede crear la imagen
            embed.description = f"{member.mention} se unió al servidor"
            await channel.send(embed=embed)

    # ═══ COMANDOS DE ADMINISTRADOR ═══

    @commands.command(name="roles_check")
    @commands.has_permissions(administrator=True)
    async def check_roles_status(self, ctx):
        """Muestra el estado de los roles automáticos"""
        base_role = ctx.guild.get_role(BASE_ROLE_ID)
        auto_role = ctx.guild.get_role(AUTO_ROLE_ID)
        
        embed = discord.Embed(
            title="🎭 Estado de Roles Automáticos",
            color=0x00ffff,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🎯 Rol Base",
            value=f"{base_role.mention if base_role else '❌ No encontrado'}\nID: `{BASE_ROLE_ID}`",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Rol Automático",
            value=f"{auto_role.mention if auto_role else '❌ No encontrado'}\nID: `{AUTO_ROLE_ID}`",
            inline=True
        )
        
        embed.add_field(
            name="👑 Prefijo de Rango",
            value=f"`{RANGO_PREFIX}`",
            inline=True
        )
        
        if base_role:
            members_with_base = len([m for m in ctx.guild.members if base_role in m.roles])
            embed.add_field(
                name="📊 Estadísticas",
                value=f"Miembros con rol base: **{members_with_base}**",
                inline=False
            )
        
        embed.add_field(
            name="📋 Comandos",
            value="`!roles_check` - Ver estado\n`!roles_fix` - Arreglar roles\n`!roles_simulate @usuario` - Simular asignación",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="roles_fix")
    @commands.has_permissions(administrator=True)
    async def fix_roles(self, ctx):
        """Arregla los roles automáticos de todos los miembros"""
        await ctx.send("🔧 Iniciando revisión masiva de roles...")
        await self.bulk_check_auto_roles(ctx.guild)
        await ctx.send("✅ Revisión masiva completada. Verifica los logs para detalles.")

    @commands.command(name="roles_simulate")
    @commands.has_permissions(administrator=True)
    async def simulate_role_assignment(self, ctx, member: discord.Member):
        """Simula la asignación de rol para un miembro específico"""
        base_role = ctx.guild.get_role(BASE_ROLE_ID)
        auto_role = ctx.guild.get_role(AUTO_ROLE_ID)
        
        if not base_role or not auto_role:
            await ctx.send("❌ Uno o ambos roles no fueron encontrados.")
            return
        
        embed = discord.Embed(
            title=f"🎭 Simulación de Roles para {member.display_name}",
            color=0x00ffff
        )
        
        has_base = base_role in member.roles
        has_auto = auto_role in member.roles
        has_rango = any(role.name.startswith(RANGO_PREFIX) for role in member.roles)
        
        embed.add_field(name="👤 Usuario", value=member.mention, inline=False)
        embed.add_field(name="🎯 Tiene rol base", value="✅" if has_base else "❌", inline=True)
        embed.add_field(name="⚙️ Tiene rol automático", value="✅" if has_auto else "❌", inline=True)
        embed.add_field(name="👑 Tiene rol de rango", value="✅" if has_rango else "❌", inline=True)
        
        # Lógica de decisión
        if has_base:
            if has_rango and has_auto:
                action = "🔄 Se debería REMOVER el rol automático"
            elif not has_rango and not has_auto:
                action = "➕ Se debería ASIGNAR el rol automático"
            elif has_rango and not has_auto:
                action = "✅ Estado correcto (tiene rango, no tiene automático)"
            elif not has_rango and has_auto:
                action = "✅ Estado correcto (no tiene rango, tiene automático)"
            else:
                action = "❓ Estado indeterminado"
        else:
            action = "⚠️ No tiene rol base, no se aplican reglas"
        
        embed.add_field(name="📋 Acción requerida", value=action, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="help_welcome", aliases=["ayuda_bienvenida", "welcome_help"])
    async def help_welcome(self, ctx):
        """Muestra ayuda completa sobre el sistema de bienvenida"""
        embed = discord.Embed(
            title="🎉 Sistema de Bienvenida - Guía Completa",
            description="Sistema automático de bienvenida con imágenes personalizadas, avatares superpuestos y gestión de roles.",
            color=0x00ffff
        )
        
        # Comandos de Administrador - Configuración
        embed.add_field(
            name="⚙️ Comandos de Configuración",
            value=(
                "`!welcome_config` - Ver configuración actual del sistema\n"
                "`!welcome_test` - Probar el sistema de bienvenida\n"
                "`!welcome_avatar` - Ver configuración de avatar\n"
                "`!welcome_avatar size <píxeles>` - Cambiar tamaño del avatar\n"
                "`!welcome_avatar position <posición>` - Cambiar posición del avatar\n"
                "`!welcome_avatar offset <x> <y>` - Ajustar posición personalizada\n"
                "`!welcome_avatar border <píxeles>` - Configurar borde del avatar"
            ),
            inline=False
        )
        
        # Comandos de Roles
        embed.add_field(
            name="🎭 Comandos de Roles",
            value=(
                "`!roles_check` - Ver estado de roles automáticos\n"
                "`!roles_fix` - Arreglar roles de todos los miembros\n"
                "`!roles_simulate @usuario` - Simular asignación de rol"
            ),
            inline=False
        )
        
        # Sistema de Roles
        embed.add_field(
            name="🎯 Sistema de Roles Automático",
            value=(
                f"**Rol Base:** <@&{BASE_ROLE_ID}>\n"
                f"**Rol Automático:** <@&{AUTO_ROLE_ID}>\n"
                f"**Prefijo de Rango:** `{RANGO_PREFIX}`\n\n"
                "**Reglas:**\n"
                "• Si tienes rol base y NO tienes rol de rango → Se asigna rol automático\n"
                "• Si tienes rol base y SÍ tienes rol de rango → Se remueve rol automático"
            ),
            inline=False
        )
        
        # Posiciones de Avatar
        embed.add_field(
            name="📍 Posiciones de Avatar Disponibles",
            value=(
                "`center` - Centro de la imagen\n"
                "`top` - Parte superior\n"
                "`bottom` - Parte inferior\n"
                "`custom` - Posición personalizada (usa offset)"
            ),
            inline=False
        )
        
        # Configuración de Archivos
        embed.add_field(
            name="📁 Archivos Requeridos",
            value=(
                "**Imagen Principal:** `resources/images/welcome.png`\n"
                "**Imagen General:** `resources/images/welcome-general.png`\n"
                "**Directorio:** Se crea automáticamente si no existe\n"
                "**Formatos:** PNG recomendado para transparencias"
            ),
            inline=False
        )
        
        # Canales Configurados
        embed.add_field(
            name="📢 Canales del Sistema",
            value=(
                f"**Canal de Bienvenida:** <#{WELCOME_CHANNEL_ID}>\n"
                f"**Canal General:** <#{GENERAL_CHANNEL_ID}>\n"
                "💡 Los IDs se configuran en el código del bot"
            ),
            inline=False
        )
        
        # Características del Sistema
        embed.add_field(
            name="✨ Características",
            value=(
                "🎨 **Imágenes personalizadas** con avatar superpuesto\n"
                "📄 **Mensajes aleatorios** de bienvenida\n"
                "⚙️ **Avatar configurable** (tamaño, posición, borde)\n"
                "🖼️ **Doble canal** (bienvenida dedicada + general)\n"
                "🎯 **Fallback automático** si fallan las imágenes\n"
                "👑 **Logo del servidor** incluido en imagen general\n"
                "🎭 **Gestión automática de roles** con reglas personalizadas"
            ),
            inline=False
        )
        
        embed.set_footer(text="💡 Usa !welcome_test para probar el sistema | Sistema de Bienvenida v3.0")
        
        await ctx.send(embed=embed)

    @commands.command(name="welcome_test")
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Prueba el sistema de bienvenida con el usuario actual"""
        await ctx.send("🧪 Probando sistema de bienvenida...")
        await self.send_welcome_message(ctx.author)
        await self.send_general_welcome(ctx.author)
        await ctx.send("✅ Test de bienvenida completado. Revisa los canales configurados.")

    @commands.command(name="welcome_config")
    @commands.has_permissions(administrator=True)
    async def welcome_config(self, ctx):
        """Muestra la configuración actual del sistema de bienvenida"""
        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        general_channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        background_exists = os.path.exists(self.background_image)
        base_role = ctx.guild.get_role(BASE_ROLE_ID)
        auto_role = ctx.guild.get_role(AUTO_ROLE_ID)
        
        embed = discord.Embed(
            title="⚙️ Configuración de Bienvenida",
            color=0x00ffff,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🎉 Canal de Bienvenida",
            value=welcome_channel.mention if welcome_channel else "❌ No encontrado",
            inline=False
        )
        
        embed.add_field(
            name="💬 Canal General",
            value=general_channel.mention if general_channel else "❌ No encontrado",
            inline=False
        )
        
        embed.add_field(
            name="🖼️ Imagen de Fondo",
            value=f"📁 Archivo: `{self.background_image}`\n{'✅ Encontrada' if background_exists else '❌ No encontrada'}",
            inline=False
        )
        
        embed.add_field(
            name="🎨 Configuración de Avatar",
            value=f"📏 Tamaño: {self.avatar_size}px\n📍 Posición: {self.avatar_position}\n🖼️ Borde: {self.avatar_border_size}px {'✅' if self.avatar_border_size > 0 else '❌'}",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Sistema de Roles",
            value=(
                f"🎯 **Rol Base:** {base_role.mention if base_role else '❌ No encontrado'}\n"
                f"⚙️ **Rol Automático:** {auto_role.mention if auto_role else '❌ No encontrado'}\n"
                f"👑 **Prefijo de Rango:** `{RANGO_PREFIX}`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Comandos",
            value="`!welcome_test` - Probar sistema\n`!welcome_config` - Ver configuración\n`!welcome_avatar` - Configurar avatar\n`!roles_check` - Estado de roles",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="welcome_avatar")
    @commands.has_permissions(administrator=True)
    async def configure_avatar(self, ctx, setting=None, *, value=None):
        """Configura el avatar superpuesto"""
        if not setting:
            embed = discord.Embed(
                title="🎨 Configuración de Avatar",
                color=0x00ffff,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="📏 Tamaño", value=f"`{self.avatar_size}` píxeles", inline=True)
            embed.add_field(name="📍 Posición", value=f"`{self.avatar_position}`", inline=True)
            embed.add_field(name="🖼️ Borde", value=f"`{self.avatar_border_size}px`", inline=True)
            
            if self.avatar_position == "custom":
                embed.add_field(
                    name="📐 Offset personalizado",
                    value=f"X: `{self.avatar_x_offset}`, Y: `{self.avatar_y_offset}`",
                    inline=False
                )
            
            embed.add_field(
                name="💡 Comandos disponibles",
                value="`!welcome_avatar size <píxeles>`\n`!welcome_avatar position <center|top|bottom|custom>`\n`!welcome_avatar offset <x> <y>`\n`!welcome_avatar border <píxeles>`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        setting = setting.lower()
        
        if setting == "size":
            if not value:
                await ctx.send("❌ Usa: `!welcome_avatar size <número>`")
                return
            try:
                new_size = int(value)
                if 50 <= new_size <= 500:
                    self.avatar_size = new_size
                    await ctx.send(f"✅ Tamaño de avatar cambiado a **{new_size}px**")
                else:
                    await ctx.send("❌ El tamaño debe estar entre 50 y 500 píxeles")
            except ValueError:
                await ctx.send("❌ Usa: `!welcome_avatar size <número>`")
        
        elif setting == "position":
            positions = ["center", "top", "bottom", "custom"]
            if value and value.lower() in positions:
                self.avatar_position = value.lower()
                await ctx.send(f"✅ Posición cambiada a **{value.lower()}**")
            else:
                await ctx.send(f"❌ Posiciones válidas: {', '.join(positions)}")
        
        elif setting == "offset":
            if self.avatar_position != "custom":
                await ctx.send("❌ Los offsets solo funcionan con posición 'custom'")
                return
            if not value:
                await ctx.send("❌ Usa: `!welcome_avatar offset <x> <y>`")
                return
            try:
                offsets = value.split()
                if len(offsets) == 2:
                    x_offset = int(offsets[0])
                    y_offset = int(offsets[1])
                    if -300 <= x_offset <= 300 and -300 <= y_offset <= 300:
                        self.avatar_x_offset = x_offset
                        self.avatar_y_offset = y_offset
                        await ctx.send(f"✅ Offset cambiado a X:**{x_offset}**, Y:**{y_offset}**")
                    else:
                        await ctx.send("❌ Los offsets deben estar entre -300 y 300")
                else:
                    await ctx.send("❌ Usa: `!welcome_avatar offset <x> <y>`")
            except ValueError:
                await ctx.send("❌ Usa números válidos: `!welcome_avatar offset <x> <y>`")
        
        elif setting == "border":
            if not value:
                await ctx.send("❌ Usa: `!welcome_avatar border <número>`")
                return
            try:
                border_size = int(value)
                if 0 <= border_size <= 20:
                    self.avatar_border_size = border_size
                    await ctx.send(f"✅ Borde cambiado a **{border_size}px**")
                else:
                    await ctx.send("❌ El borde debe estar entre 0 y 20 píxeles")
            except ValueError:
                await ctx.send("❌ Usa: `!welcome_avatar border <número>`")
        
        else:
            await ctx.send("❌ Configuración no válida. Usa `!welcome_avatar` para ver opciones.")

    @commands.Cog.listener()
    async def on_ready(self):
        import asyncio
        print("[WelcomeSystem] Sistema de bienvenida con roles automáticos listo")
        
        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        general_channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        base_role = None
        auto_role = None
        
        # Obtener roles si hay guilds disponibles
        if self.bot.guilds:
            guild = self.bot.guilds[0]  # Usar el primer servidor
            base_role = guild.get_role(BASE_ROLE_ID)
            auto_role = guild.get_role(AUTO_ROLE_ID)
        
        # Verificar canales
        if not welcome_channel:
            print(f"⚠️ Canal de bienvenida {WELCOME_CHANNEL_ID} no encontrado")
        if not general_channel:
            print(f"⚠️ Canal general {GENERAL_CHANNEL_ID} no encontrado")
        
        # Verificar roles
        if not base_role:
            print(f"⚠️ Rol base {BASE_ROLE_ID} no encontrado")
        if not auto_role:
            print(f"⚠️ Rol automático {AUTO_ROLE_ID} no encontrado")
        
        # Verificar directorios e imágenes
        if not os.path.exists(self.background_dir):
            print(f"⚠️ Directorio {self.background_dir} no encontrado, creándolo...")
            os.makedirs(self.background_dir, exist_ok=True)
        
        if os.path.exists(self.background_image):
            print(f"✅ Imagen de fondo encontrada: {self.background_image}")
        else:
            print(f"⚠️ Imagen de fondo no encontrada: {self.background_image}")
            print("💡 Tip: Coloca tu imagen welcome.png en resources/images/")
        
        # Mostrar configuración de roles
        print(f"🎭 Sistema de roles configurado:")
        print(f"   📍 Rol base: {base_role.name if base_role else 'No encontrado'} (ID: {BASE_ROLE_ID})")
        print(f"   ⚙️ Rol automático: {auto_role.name if auto_role else 'No encontrado'} (ID: {AUTO_ROLE_ID})")
        print(f"   👑 Prefijo de rango: '{RANGO_PREFIX}'")

async def setup(bot: commands.Bot):
    # Importar asyncio si no está disponible
    import asyncio
    await bot.add_cog(WelcomeSystem(bot))