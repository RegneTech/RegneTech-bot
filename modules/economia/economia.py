import discord
from discord.ext import commands
from discord.ui import View, Button
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import os
import re
from database import (
    get_user_balance, 
    update_user_balance, 
    add_transaction, 
    get_user_transactions,
    use_product,
    add_product,
    get_all_products,
    get_product,
    update_product,
    delete_product,
    purchase_product,
    get_user_inventory,
    get_economia_stats
)

class ConfirmPurchaseView(View):
    def __init__(self, user_id, producto, precio):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.producto = producto
        self.precio = precio
    
    @discord.ui.button(label='✅ Confirmar', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes confirmar esta compra.", ephemeral=True)
            return
        
        # Verificar saldo nuevamente
        saldo_actual = await database.get_user_balance(self.user_id)
        if saldo_actual < self.precio:
            embed = discord.Embed(
                title="❌ Saldo insuficiente",
                description=f"Tu saldo actual es €{saldo_actual:.2f}",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        # Procesar compra
        success, message = await database.purchase_product(self.user_id, self.producto, self.precio)
        
        if success:
            nuevo_saldo = await database.get_user_balance(self.user_id)
            embed = discord.Embed(
                title="✅ Compra exitosa",
                description=f"Has comprado **{self.producto}** por €{self.precio:.2f}\nSaldo restante: €{nuevo_saldo:.2f}",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error en la compra",
                description=message,
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label='❌ Cancelar', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes cancelar esta compra.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Compra cancelada",
            description="Has cancelado la compra.",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)


class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configuración - IDs configurados
        self.LOG_CHANNEL_ID = 1400106793811705863
        self.SHOP_CHANNEL_ID = 1400106793551663189
        self.STAFF_ROLE_ID = 1400106792280658070
    
    def is_admin_or_staff(self, ctx):
        """Verifica si el usuario es administrador o staff"""
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Verificar por ID del rol si está configurado
        if self.STAFF_ROLE_ID:
            staff_role = discord.utils.get(ctx.guild.roles, id=self.STAFF_ROLE_ID)
            if staff_role and staff_role in ctx.author.roles:
                return True
        
        return False
    
    async def log_operation(self, ctx, operation_type, details):
        """Registra operaciones en el canal de logs"""
        if self.LOG_CHANNEL_ID:
            log_channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title=f"📊 {operation_type}",
                    description=details,
                    color=0x3498db,
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Ejecutado por {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
                await log_channel.send(embed=embed)
    
    def parse_role_mention(self, text):
        """Extrae el ID del rol de una mención @rol o <@&ID>"""
        # Patrón para menciones de rol: <@&123456789>
        role_mention_pattern = r'<@&(\d+)>'
        match = re.search(role_mention_pattern, text)
        if match:
            return int(match.group(1))
        
        # Si no es una mención, intentar convertir directamente a int
        try:
            return int(text)
        except ValueError:
            return None
    
    # COMANDOS PARA ADMINISTRADORES
    
    @commands.command(name="dar_dinero")
    async def dar_dinero(self, ctx, usuario: discord.Member, monto: float):
        """Agrega dinero al saldo de un usuario"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            monto_decimal = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if monto_decimal <= 0:
                await ctx.send("❌ El monto debe ser positivo.")
                return
            
            saldo_actual = await database.get_user_balance(usuario.id)
            nuevo_saldo = saldo_actual + monto_decimal
            
            await database.update_user_balance(
                usuario.id, 
                nuevo_saldo, 
                ctx.author.id, 
                'DEPOSITO', 
                f'Depósito de €{monto_decimal:.2f} por {ctx.author}'
            )
            
            embed = discord.Embed(
                title="✅ Dinero agregado",
                description=f"Se han agregado **€{monto_decimal:.2f}** al saldo de {usuario.mention}\n"
                           f"Saldo anterior: €{saldo_actual:.2f}\n"
                           f"Saldo actual: €{nuevo_saldo:.2f}",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
            
            await self.log_operation(ctx, "Depósito", f"€{monto_decimal:.2f} agregados a {usuario.mention}")
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="quitar_dinero")
    async def quitar_dinero(self, ctx, usuario: discord.Member, monto: float):
        """Resta dinero del saldo de un usuario"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            monto_decimal = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if monto_decimal <= 0:
                await ctx.send("❌ El monto debe ser positivo.")
                return
            
            saldo_actual = await database.get_user_balance(usuario.id)
            nuevo_saldo = saldo_actual - monto_decimal
            
            if nuevo_saldo < 0:
                await ctx.send("⚠️ Esta operación dejaría el saldo en negativo. ¿Continuar? (s/n)")
                
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['s', 'n', 'si', 'no']
                
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                    if msg.content.lower() in ['n', 'no']:
                        await ctx.send("❌ Operación cancelada.")
                        return
                except asyncio.TimeoutError:
                    await ctx.send("❌ Tiempo de espera agotado. Operación cancelada.")
                    return
            
            await database.update_user_balance(
                usuario.id, 
                nuevo_saldo, 
                ctx.author.id, 
                'RETIRO', 
                f'Retiro de €{monto_decimal:.2f} por {ctx.author}'
            )
            
            embed = discord.Embed(
                title="✅ Dinero retirado",
                description=f"Se han retirado **€{monto_decimal:.2f}** del saldo de {usuario.mention}\n"
                           f"Saldo anterior: €{saldo_actual:.2f}\n"
                           f"Saldo actual: €{nuevo_saldo:.2f}",
                color=0xff9900
            )
            await ctx.send(embed=embed)
            
            await self.log_operation(ctx, "Retiro", f"€{monto_decimal:.2f} retirados de {usuario.mention}")
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="setear_dinero")
    async def setear_dinero(self, ctx, usuario: discord.Member, monto: float):
        """Establece el saldo exacto de un usuario"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            monto_decimal = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if monto_decimal < 0:
                await ctx.send("❌ El saldo no puede ser negativo.")
                return
            
            saldo_actual = await database.get_user_balance(usuario.id)
            
            await database.update_user_balance(
                usuario.id, 
                monto_decimal, 
                ctx.author.id, 
                'AJUSTE', 
                f'Saldo establecido a €{monto_decimal:.2f} por {ctx.author}'
            )
            
            embed = discord.Embed(
                title="✅ Saldo establecido",
                description=f"El saldo de {usuario.mention} ha sido establecido a **€{monto_decimal:.2f}**\n"
                           f"Saldo anterior: €{saldo_actual:.2f}",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            
            await self.log_operation(ctx, "Ajuste de saldo", f"Saldo de {usuario.mention} establecido a €{monto_decimal:.2f}")
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="historial")
    async def historial(self, ctx, usuario: discord.Member):
        """Muestra el historial de transacciones de un usuario"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        transacciones = await database.get_user_transactions(usuario.id)
        
        if not transacciones:
            embed = discord.Embed(
                title="📊 Historial de transacciones",
                description=f"{usuario.mention} no tiene transacciones registradas.",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Historial de transacciones",
            description=f"Últimas 20 transacciones de {usuario.mention}",
            color=0x3498db
        )
        
        for i, (tipo, monto, descripcion, timestamp, ejecutado_por) in enumerate(transacciones[:10]):
            fecha = timestamp.strftime("%d/%m/%Y %H:%M")
            monto_str = f"€{monto:.2f}" if monto else "N/A"
            
            embed.add_field(
                name=f"{tipo} - {fecha}",
                value=f"{descripcion}\nMonto: {monto_str}",
                inline=False
            )
        
        saldo_actual = await database.get_user_balance(usuario.id)
        embed.set_footer(text=f"Saldo actual: €{saldo_actual:.2f}")
        
        await ctx.send(embed=embed)
    
    # COMANDOS PARA USUARIOS
    
    @commands.command(name="saldo")
    async def saldo(self, ctx):
        """Muestra el saldo actual del usuario"""
        saldo = await database.get_user_balance(ctx.author.id)
        
        embed = discord.Embed(
            title="💰 Tu saldo",
            description=f"Tienes **€{saldo:.2f}** en tu cuenta",
            color=0x27ae60
        )
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="inventario")
    async def inventario(self, ctx):
        """Muestra el inventario del usuario"""
        inventario = await database.get_user_inventory(ctx.author.id)
        
        if not inventario:
            embed = discord.Embed(
                title="📦 Tu inventario",
                description="No tienes productos en tu inventario.",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📦 Tu inventario",
            description="Productos que has comprado:",
            color=0x9b59b6
        )
        
        for producto, cantidad, precio_promedio, role_id in inventario:
            value_text = f"Cantidad: {cantidad}\nPrecio promedio: €{precio_promedio:.2f}"
            
            if role_id:
                role = discord.utils.get(ctx.guild.roles, id=role_id)
                if role:
                    value_text += f"\nUsa `!use \"{producto}\"` para obtener: {role.name}"
                else:
                    value_text += f"\nUsa `!use \"{producto}\"` para obtener rol"
            
            embed.add_field(
                name=f"{producto}",
                value=value_text,
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    # COMANDOS DE TIENDA - ADMINISTRADORES
    
    @commands.command(name="agregar_producto")
    async def agregar_producto(self, ctx, *, args):
        """Agrega un producto a la tienda
        Uso: !agregar_producto "Nombre del producto" precio cantidad @rol
        Ejemplo: !agregar_producto "VIP" 50.00 10 @VIP"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            # Parsear argumentos: "nombre" precio cantidad @rol
            if not args.startswith('"'):
                await ctx.send('❌ Uso: `!agregar_producto "Nombre del producto" precio cantidad @rol`\nEl nombre debe estar entre comillas.')
                return
            
            # Extraer el nombre del producto entre comillas
            end_quote = args.find('"', 1)
            if end_quote == -1:
                await ctx.send("❌ Nombre del producto debe estar entre comillas.")
                return
            
            nombre = args[1:end_quote]
            remaining = args[end_quote+1:].strip()
            
            # Separar los argumentos restantes
            parts = remaining.split()
            
            if len(parts) < 2:
                await ctx.send("❌ Faltan argumentos: precio y cantidad son obligatorios.")
                return
            
            # Extraer precio y cantidad
            try:
                precio = float(parts[0])
                cantidad = int(parts[1])
            except ValueError:
                await ctx.send("❌ El precio debe ser un número decimal y la cantidad un número entero.")
                return
            
            if precio <= 0 or cantidad <= 0:
                await ctx.send("❌ El precio y la cantidad deben ser positivos.")
                return
            
            role_id = None
            role_name = None
            
            # Verificar si se proporcionó un rol
            if len(parts) >= 3:
                # Unir las partes restantes para manejar menciones de rol
                role_part = ' '.join(parts[2:])
                
                # Intentar encontrar el rol por mención, ID o nombre
                role = None
                
                # 1. Intentar como mención <@&ID>
                role_id_parsed = self.parse_role_mention(role_part)
                if role_id_parsed:
                    role = discord.utils.get(ctx.guild.roles, id=role_id_parsed)
                
                # 2. Si no es mención, intentar buscar por nombre (removiendo @)
                if not role:
                    role_name_clean = role_part.lstrip('@')
                    role = discord.utils.get(ctx.guild.roles, name=role_name_clean)
                
                if not role:
                    await ctx.send(f"❌ No se encontró el rol: `{role_part}`\nAsegúrate de mencionar el rol correctamente (@rol) o usar su nombre exacto.")
                    return
                
                role_id = role.id
                role_name = role.name
            
            precio_decimal = Decimal(str(precio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if await database.add_product(nombre, precio_decimal, cantidad, role_id):
                embed = discord.Embed(
                    title="✅ Producto agregado",
                    description=f"**{nombre}** ha sido agregado a la tienda",
                    color=0x00ff00
                )
                embed.add_field(name="Precio", value=f"€{precio_decimal:.2f}", inline=True)
                embed.add_field(name="Cantidad", value=str(cantidad), inline=True)
                
                if role_id and role_name:
                    embed.add_field(name="Rol asociado", value=f"@{role_name}", inline=False)
                    embed.add_field(name="Instrucción", value=f"Los usuarios podrán usar `!use \"{nombre}\"` para obtener el rol", inline=False)
                
                await ctx.send(embed=embed)
                
                log_details = f"{nombre} - €{precio_decimal:.2f} - {cantidad} unidades"
                if role_id and role_name:
                    log_details += f" - Rol: @{role_name}"
                
                await self.log_operation(ctx, "Producto agregado", log_details)
            else:
                await ctx.send("❌ Ya existe un producto con ese nombre.")
                
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="editar_producto")
    async def editar_producto(self, ctx, *, args):
        """Edita un producto existente"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            # Parsear argumentos: "nombre" [nuevo_precio] [nueva_cantidad]
            parts = args.split()
            if len(parts) < 2:
                await ctx.send("❌ Uso: `!editar_producto \"Nombre\" nuevo_precio nueva_cantidad`")
                return
            
            # Extraer nombre
            if args.startswith('"'):
                end_quote = args.find('"', 1)
                if end_quote == -1:
                    await ctx.send("❌ Nombre del producto debe estar entre comillas.")
                    return
                nombre = args[1:end_quote]
                remaining = args[end_quote+1:].strip().split()
            else:
                nombre = parts[0]
                remaining = parts[1:]
            
            nuevo_precio = None
            nueva_cantidad = None
            
            if len(remaining) >= 1:
                nuevo_precio = Decimal(str(float(remaining[0]))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if len(remaining) >= 2:
                nueva_cantidad = int(remaining[1])
            
            if await database.update_product(nombre, nuevo_precio, nueva_cantidad):
                embed = discord.Embed(
                    title="✅ Producto actualizado",
                    description=f"**{nombre}** ha sido actualizado",
                    color=0x00ff00
                )
                if nuevo_precio:
                    embed.add_field(name="Nuevo precio", value=f"€{nuevo_precio:.2f}", inline=True)
                if nueva_cantidad:
                    embed.add_field(name="Nueva cantidad", value=str(nueva_cantidad), inline=True)
                
                await ctx.send(embed=embed)
                
                changes = []
                if nuevo_precio:
                    changes.append(f"precio: €{nuevo_precio:.2f}")
                if nueva_cantidad:
                    changes.append(f"cantidad: {nueva_cantidad}")
                
                await self.log_operation(ctx, "Producto editado", f"{nombre} - {', '.join(changes)}")
            else:
                await ctx.send("❌ Producto no encontrado.")
                
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="eliminar_producto")
    async def eliminar_producto(self, ctx, *, nombre):
        """Elimina un producto de la tienda"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        # Remover comillas si las hay
        if nombre.startswith('"') and nombre.endswith('"'):
            nombre = nombre[1:-1]
        
        if await database.delete_product(nombre):
            embed = discord.Embed(
                title="✅ Producto eliminado",
                description=f"**{nombre}** ha sido eliminado de la tienda",
                color=0xff9900
            )
            await ctx.send(embed=embed)
            
            await self.log_operation(ctx, "Producto eliminado", nombre)
        else:
            await ctx.send("❌ Producto no encontrado.")
    
    # COMANDOS DE TIENDA - USUARIOS
    
    @commands.command(name="tienda")
    async def tienda(self, ctx):
        """Muestra el catálogo de productos disponibles"""
        productos = await database.get_all_products()
        
        if not productos:
            embed = discord.Embed(
                title="🛒 Tienda",
                description="No hay productos disponibles en este momento.",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏪 Tienda",
            description="Productos disponibles para comprar:",
            color=0xe74c3c
        )
        
        for nombre, precio, cantidad, role_id in productos:
            value_text = f"Precio: €{precio:.2f}\nStock: {cantidad}"
            
            if role_id:
                role = discord.utils.get(ctx.guild.roles, id=role_id)
                if role:
                    value_text += f"\nOtorga rol: @{role.name}"
                else:
                    value_text += f"\nOtorga rol: ID {role_id}"
            
            embed.add_field(
                name=f"{nombre}",
                value=value_text,
                inline=True
            )
        
        embed.set_footer(text="Usa !comprar \"Nombre del producto\" para comprar")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="comprar")
    async def comprar(self, ctx, *, nombre):
        """Compra un producto de la tienda"""
        # Remover comillas si las hay
        if nombre.startswith('"') and nombre.endswith('"'):
            nombre = nombre[1:-1]
        
        # Verificar que el producto existe
        producto = await database.get_product(nombre)
        if not producto:
            await ctx.send("❌ Producto no encontrado.")
            return
        
        nombre_producto, precio, cantidad, role_id = producto
        precio_decimal = Decimal(str(precio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if cantidad <= 0:
            await ctx.send("❌ Producto sin stock.")
            return
        
        # Verificar saldo del usuario
        saldo_actual = await database.get_user_balance(ctx.author.id)
        if saldo_actual < precio_decimal:
            embed = discord.Embed(
                title="❌ Saldo insuficiente",
                description=f"El producto **{nombre_producto}** cuesta €{precio_decimal:.2f}\n"
                           f"Tu saldo actual es €{saldo_actual:.2f}\n"
                           f"Te faltan €{(precio_decimal - saldo_actual):.2f}",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        # Mostrar confirmación
        embed = discord.Embed(
            title="🛒 Confirmar compra",
            description=f"¿Deseas comprar **{nombre_producto}** por €{precio_decimal:.2f}?\n\n"
                       f"Tu saldo actual: €{saldo_actual:.2f}\n"
                       f"Saldo después de la compra: €{(saldo_actual - precio_decimal):.2f}",
            color=0xf39c12
        )
        
        # Agregar información del rol si existe
        if role_id:
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            if role:
                embed.add_field(
                    name="Rol incluido",
                    value=f"Al usar este producto obtendrás: @{role.name}",
                    inline=False
                )
        
        view = ConfirmPurchaseView(ctx.author.id, nombre_producto, precio_decimal)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="use")
    async def use_product(self, ctx, *, nombre):
        """Usa un producto del inventario para obtener un rol"""
        # Remover comillas si las hay
        if nombre.startswith('"') and nombre.endswith('"'):
            nombre = nombre[1:-1]
        
        # Verificar que el usuario tiene el producto en su inventario
        inventario = await database.get_user_inventory(ctx.author.id)
        producto_encontrado = None
        
        for producto, cantidad, precio_promedio, role_id in inventario:
            if producto.lower() == nombre.lower():
                producto_encontrado = (producto, role_id)
                break
        
        if not producto_encontrado:
            await ctx.send("❌ No tienes este producto en tu inventario.")
            return
        
        producto_nombre, role_id = producto_encontrado
        
        # Verificar si el producto tiene un rol asociado
        if not role_id:
            await ctx.send("❌ Este producto no otorga ningún rol.")
            return
        
        # Verificar que el rol existe
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        if not role:
            await ctx.send(f"❌ El rol asociado a este producto ya no existe (ID: {role_id})")
            return
        
        # Verificar si el usuario ya tiene el rol
        if role in ctx.author.roles:
            await ctx.send(f"❌ Ya tienes el rol **@{role.name}**.")
            return
        
        # Usar el producto
        success, result = await database.use_product(ctx.author.id, producto_nombre)
        
        if not success:
            await ctx.send(f"❌ {result}")
            return
        
        try:
            # Otorgar el rol al usuario
            await ctx.author.add_roles(role, reason=f"Producto usado: {producto_nombre}")
            
            embed = discord.Embed(
                title="✅ Producto usado",
                description=f"Has usado **{producto_nombre}** y obtenido el rol **@{role.name}**!\n"
                           f"El producto ha sido removido de tu inventario.",
                color=0x00ff00
            )
            embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            await ctx.send(embed=embed)
            
            # Log de la operación
            await self.log_operation(ctx, "Producto usado", 
                                   f"{ctx.author.mention} usó {producto_nombre} y obtuvo el rol @{role.name}")
            
        except discord.Forbidden:
            # Si no se pudo otorgar el rol, informar del error
            embed = discord.Embed(
                title="❌ Error de permisos",
                description=f"No tengo permisos para otorgar el rol **@{role.name}**.\n"
                           f"El producto se ha consumido pero no se pudo otorgar el rol.\n"
                           f"Contacta con un administrador.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            
            # Log del error
            await self.log_operation(ctx, "Error - Producto usado", 
                                   f"{ctx.author.mention} usó {producto_nombre} pero no se pudo otorgar el rol @{role.name} (permisos)")
            
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="❌ Error al otorgar rol",
                description=f"Error al otorgar el rol **@{role.name}**: {str(e)}\n"
                           f"El producto se ha consumido pero no se pudo otorgar el rol.\n"
                           f"Contacta con un administrador.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            
            # Log del error
            await self.log_operation(ctx, "Error - Producto usado", 
                                   f"{ctx.author.mention} usó {producto_nombre} pero hubo un error: {str(e)}")
    
    # COMANDO EXTRA: TRANSFERENCIAS
    
    @commands.command(name="transferir")
    async def transferir(self, ctx, usuario: discord.Member, monto: float):
        """Transfiere dinero a otro usuario (requiere aprobación de staff)"""
        if usuario.id == ctx.author.id:
            await ctx.send("❌ No puedes transferirte dinero a ti mismo.")
            return
        
        try:
            monto_decimal = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if monto_decimal <= 0:
                await ctx.send("❌ El monto debe ser positivo.")
                return
            
            # Verificar saldo
            saldo_actual = await database.get_user_balance(ctx.author.id)
            if saldo_actual < monto_decimal:
                await ctx.send(f"❌ Saldo insuficiente. Tu saldo actual es €{saldo_actual:.2f}")
                return
            
            # Solicitar aprobación de staff
            embed = discord.Embed(
                title="💸 Solicitud de transferencia",
                description=f"{ctx.author.mention} quiere transferir €{monto_decimal:.2f} a {usuario.mention}\n\n"
                           f"**Staff**: Reacciona con ✅ para aprobar o ❌ para rechazar",
                color=0xf39c12
            )
            
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            def check_reaction(reaction, user):
                return (reaction.message.id == msg.id and 
                       str(reaction.emoji) in ["✅", "❌"] and 
                       not user.bot and
                       (user.guild_permissions.administrator or 
                        (self.STAFF_ROLE_ID and discord.utils.get(user.roles, id=self.STAFF_ROLE_ID))))
            
            try:
                reaction, staff_user = await self.bot.wait_for('reaction_add', check=check_reaction, timeout=300.0)
                
                if str(reaction.emoji) == "✅":
                    # Procesar transferencia
                    saldo_emisor = await database.get_user_balance(ctx.author.id)
                    saldo_receptor = await database.get_user_balance(usuario.id)
                    
                    if saldo_emisor < monto_decimal:
                        await ctx.send("❌ El emisor ya no tiene saldo suficiente.")
                        return
                    
                    # Actualizar saldos
                    nuevo_saldo_emisor = saldo_emisor - monto_decimal
                    nuevo_saldo_receptor = saldo_receptor + monto_decimal
                    
                    await database.update_user_balance(
                        ctx.author.id, 
                        nuevo_saldo_emisor, 
                        staff_user.id, 
                        'TRANSFERENCIA_SALIDA', 
                        f'Transferencia de €{monto_decimal:.2f} a {usuario} (aprobada por {staff_user})'
                    )
                    
                    await database.update_user_balance(
                        usuario.id, 
                        nuevo_saldo_receptor, 
                        staff_user.id, 
                        'TRANSFERENCIA_ENTRADA', 
                        f'Transferencia de €{monto_decimal:.2f} desde {ctx.author} (aprobada por {staff_user})'
                    )
                    
                    embed = discord.Embed(
                        title="✅ Transferencia aprobada",
                        description=f"€{monto_decimal:.2f} transferidos de {ctx.author.mention} a {usuario.mention}\n"
                                   f"Aprobado por {staff_user.mention}",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)
                    
                    await self.log_operation(ctx, "Transferencia", 
                                           f"€{monto_decimal:.2f} de {ctx.author.mention} a {usuario.mention} (aprobada por {staff_user.mention})")
                
                else:
                    embed = discord.Embed(
                        title="❌ Transferencia rechazada",
                        description=f"La transferencia fue rechazada por {staff_user.mention}",
                        color=0xff0000
                    )
                    await ctx.send(embed=embed)
                    
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Transferencia expirada",
                    description="La solicitud de transferencia ha expirado.",
                    color=0x95a5a6
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    # COMANDOS ADICIONALES DE ADMINISTRACIÓN
    
    @commands.command(name="economia_stats")
    async def economia_stats(self, ctx):
        """Muestra estadísticas generales del sistema económico"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            stats = await database.get_economia_stats()
            
            embed = discord.Embed(
                title="📊 Estadísticas del Sistema Económico",
                color=0x3498db
            )
            
            embed.add_field(
                name="💰 Dinero en circulación",
                value=f"€{stats['total_dinero']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="👥 Usuarios registrados",
                value=f"{stats['total_usuarios']} total\n{stats['usuarios_con_saldo']} con saldo",
                inline=True
            )
            
            embed.add_field(
                name="🏪 Tienda",
                value=f"{stats['total_productos']} productos\n€{stats['valor_tienda']:.2f} valor total",
                inline=True
            )
            
            embed.add_field(
                name="📈 Actividad hoy",
                value=f"{stats['transacciones_hoy']} transacciones",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error al obtener estadísticas: {str(e)}")
    
    @commands.command(name="backup_economia")
    async def backup_economia(self, ctx):
        """Crea un backup de la base de datos económica (solo informativo para PostgreSQL)"""
        if not self.is_admin_or_staff(ctx):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            embed = discord.Embed(
                title="ℹ️ Backup PostgreSQL",
                description=f"Para crear un backup de PostgreSQL, usa:\n"
                           f"`pg_dump {os.getenv('DATABASE_URL', 'DATABASE_URL')} > backup_{timestamp}.sql`\n\n"
                           f"O contacta con el administrador del servidor.",
                color=0x3498db
            )
            
            await ctx.send(embed=embed)
            await self.log_operation(ctx, "Backup solicitado", f"Timestamp: {timestamp}")
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="help_economia")
    async def help_economia(self, ctx):
        """Muestra la ayuda del sistema económico"""
        embed = discord.Embed(
            title="💡 Sistema de Economía - Ayuda",
            description="Comandos disponibles del sistema económico",
            color=0x9b59b6
        )
        
        if self.is_admin_or_staff(ctx):
            embed.add_field(
                name="👑 Comandos de Administrador",
                value="`!dar_dinero @usuario monto` - Agregar dinero\n"
                      "`!quitar_dinero @usuario monto` - Quitar dinero\n"
                      "`!setear_dinero @usuario monto` - Establecer saldo\n"
                      "`!historial @usuario` - Ver transacciones\n"
                      "`!economia_stats` - Ver estadísticas\n"
                      "`!backup_economia` - Info sobre backup",
                inline=False
            )
            
            embed.add_field(
                name="🏪 Gestión de Tienda",
                value='`!agregar_producto "nombre" precio cantidad @rol`\n'
                      '`!editar_producto "nombre" precio cantidad`\n'
                      '`!eliminar_producto "nombre"`\n\n'
                      '**Ejemplo:** `!agregar_producto "VIP" 50.00 10 @VIP`',
                inline=False
            )
        
        embed.add_field(
            name="👤 Comandos de Usuario",
            value="`!saldo` - Ver tu saldo\n"
                  "`!inventario` - Ver tus productos\n"
                  "`!tienda` - Ver productos disponibles\n"
                  '`!comprar "nombre"` - Comprar producto\n'
                  '`!use "nombre"` - Usar producto (obtener rol)\n'
                  "`!transferir @usuario monto` - Transferir dinero",
            inline=False
        )
        
        embed.set_footer(text="💰 Sistema de economía con euros y roles automáticos")
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economia(bot))