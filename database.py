import os
import asyncpg
import asyncio
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

DB_URL = os.getenv("DATABASE_URL")

pool = None

async def create_pool():
    return await asyncpg.create_pool(DB_URL, ssl="require")

async def init_database():
    global pool
    pool = await create_pool()
    
    async with pool.acquire() as conn:
        # Tabla de bumps (sistema de bump tracker)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS bumps (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, guild_id)
        );
        """)
        
        # Tabla de conteo de bumps
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS bump_counts (
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        );
        """)
        
        # Tabla de usuarios del sistema económico
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id BIGINT PRIMARY KEY,
            saldo DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Tabla de productos en la tienda
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            precio DECIMAL(10,2) NOT NULL,
            cantidad INTEGER NOT NULL,
            role_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Tabla de inventario de usuarios
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            producto_nombre TEXT NOT NULL,
            cantidad INTEGER DEFAULT 1,
            precio_compra DECIMAL(10,2),
            fecha_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
        );
        """)
        
        # Tabla de transacciones (historial económico)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            tipo TEXT NOT NULL,
            monto DECIMAL(10,2),
            descripcion TEXT,
            ejecutado_por BIGINT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES usuarios (user_id)
        );
        """)
        
        # Tabla principal de invitaciones
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            invited_by_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            invite_code TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        """)
        
        # === TABLAS DEL SISTEMA DE NIVELES ===
        
        # Tabla principal de usuarios para el sistema de niveles
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS levels_users (
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            xp BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_xp_time BIGINT DEFAULT 0,
            total_messages INTEGER DEFAULT 0,
            weekly_xp BIGINT DEFAULT 0,
            monthly_xp BIGINT DEFAULT 0,
            badges JSONB DEFAULT '[]'::jsonb,
            join_date BIGINT DEFAULT 0,
            voice_time INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        );
        """)
        
        # Tabla de configuración de roles por nivel
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id BIGINT NOT NULL,
            level INTEGER NOT NULL,
            role_id BIGINT NOT NULL,
            PRIMARY KEY (guild_id, level)
        );
        """)
        
        # Tabla de configuración del servidor para niveles
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id BIGINT PRIMARY KEY,
            level_up_channel BIGINT,
            xp_per_message INTEGER DEFAULT 15,
            xp_cooldown INTEGER DEFAULT 60,
            enabled_channels JSONB DEFAULT '[]'::jsonb,
            disabled_channels JSONB DEFAULT '[]'::jsonb,
            xp_multiplier DECIMAL(3,1) DEFAULT 1.0,
            level_formula TEXT DEFAULT 'exponential',
            voice_xp_enabled BOOLEAN DEFAULT FALSE,
            voice_xp_rate INTEGER DEFAULT 5,
            bonus_roles JSONB DEFAULT '[]'::jsonb,
            announce_level_up BOOLEAN DEFAULT TRUE,
            stack_roles BOOLEAN DEFAULT FALSE,
            custom_rewards JSONB DEFAULT '{}'::jsonb
        );
        """)
        
        # Tabla de insignias mejorada
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            badge_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            emoji TEXT,
            requirement_type TEXT,
            requirement_value INTEGER,
            rarity TEXT DEFAULT 'common',
            hidden BOOLEAN DEFAULT FALSE
        );
        """)
        
        # Tabla de recompensas personalizadas
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_rewards (
            guild_id BIGINT NOT NULL,
            level INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            reward_data TEXT,
            PRIMARY KEY (guild_id, level, reward_type)
        );
        """)
        
        # Tabla de sesiones de voz
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS voice_sessions (
            user_id BIGINT NOT NULL,
            guild_id BIGINT NOT NULL,
            join_time BIGINT NOT NULL,
            leave_time BIGINT DEFAULT 0,
            xp_earned INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id, join_time)
        );
        """)
        
        # Índices para mejor rendimiento
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_invites_user_id ON invites(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_invites_invited_by_id ON invites(invited_by_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_invites_guild_id ON invites(guild_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_invites_active ON invites(guild_id, is_active)')
        
        # Índices para el sistema de niveles
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_levels_users_xp ON levels_users(guild_id, xp DESC)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_levels_users_level ON levels_users(guild_id, level DESC)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_levels_users_weekly ON levels_users(guild_id, weekly_xp DESC)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_levels_users_monthly ON levels_users(guild_id, monthly_xp DESC)')

async def fetch(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def execute(query, *args):
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

# ==========================================
# FUNCIONES PARA EL SISTEMA DE BUMPS
# ==========================================

async def add_bump(user_id: int, guild_id: int) -> int:
    """Agrega un bump y retorna el total de bumps del usuario"""
    async with pool.acquire() as conn:
        # Insertar o actualizar el registro de bump más reciente
        await conn.execute("""
            INSERT INTO bumps (user_id, guild_id, timestamp) 
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET timestamp = CURRENT_TIMESTAMP
        """, user_id, guild_id)
        
        # Actualizar contador
        await conn.execute("""
            INSERT INTO bump_counts (user_id, guild_id, count) 
            VALUES ($1, $2, 1)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET count = bump_counts.count + 1
        """, user_id, guild_id)
        
        # Obtener total actual
        result = await conn.fetchrow(
            "SELECT count FROM bump_counts WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )
        return result['count'] if result else 1

async def get_bumps(user_id: int, guild_id: int) -> int:
    """Obtiene el número total de bumps de un usuario en un servidor"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT count FROM bump_counts WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )
        return result['count'] if result else 0

async def get_all_bumps(guild_id: int) -> list:
    """Obtiene el ranking de bumps de un servidor"""
    async with pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT user_id, count 
            FROM bump_counts 
            WHERE guild_id = $1 
            ORDER BY count DESC
        """, guild_id)
        return [(row['user_id'], row['count']) for row in results]

# ==========================================
# FUNCIONES PARA EL SISTEMA ECONÓMICO
# ==========================================

async def get_user_balance(user_id: int) -> Decimal:
    """Obtiene el saldo de un usuario"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow('SELECT saldo FROM usuarios WHERE user_id = $1', user_id)
        
        if result is None:
            await conn.execute('INSERT INTO usuarios (user_id, saldo) VALUES ($1, 0.00)', user_id)
            return Decimal('0.00')
        
        return Decimal(str(result['saldo'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

async def update_user_balance(user_id: int, new_balance: Decimal, admin_id: int, operation_type: str, description: str):
    """Actualiza el saldo de un usuario y registra la transacción"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Asegurar que el usuario existe
            await conn.execute(
                'INSERT INTO usuarios (user_id, saldo) VALUES ($1, 0.00) ON CONFLICT (user_id) DO NOTHING',
                user_id
            )
            
            # Actualizar saldo
            await conn.execute(
                'UPDATE usuarios SET saldo = $1 WHERE user_id = $2',
                float(new_balance), user_id
            )
            
            # Registrar transacción
            await conn.execute("""
                INSERT INTO transacciones (user_id, tipo, monto, descripcion, ejecutado_por)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, operation_type, float(new_balance), description, admin_id)

async def add_transaction(user_id: int, tipo: str, monto: float, descripcion: str, ejecutado_por: int = None):
    """Registra una transacción"""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transacciones (user_id, tipo, monto, descripcion, ejecutado_por)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, tipo, monto, descripcion, ejecutado_por)

async def get_user_transactions(user_id: int) -> list:
    """Obtiene el historial de transacciones de un usuario"""
    async with pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT tipo, monto, descripcion, timestamp, ejecutado_por
            FROM transacciones 
            WHERE user_id = $1 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, user_id)
        
        return [(row['tipo'], row['monto'], row['descripcion'], 
                row['timestamp'], row['ejecutado_por']) for row in results]

async def use_product(user_id: int, producto_nombre: str) -> tuple[bool, str]:
    """Usa un producto del inventario del usuario"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                # Verificar que el usuario tiene el producto
                item = await conn.fetchrow("""
                    SELECT id FROM inventario 
                    WHERE user_id = $1 AND producto_nombre = $2 
                    LIMIT 1
                """, user_id, producto_nombre)
                
                if not item:
                    return False, "No tienes este producto en tu inventario"
                
                # Obtener información del producto (especialmente role_id)
                product_info = await conn.fetchrow(
                    'SELECT role_id FROM productos WHERE nombre = $1', 
                    producto_nombre
                )
                
                role_id = product_info['role_id'] if product_info else None
                
                # Eliminar el producto del inventario
                await conn.execute('DELETE FROM inventario WHERE id = $1', item['id'])
                
                # Registrar el uso
                await conn.execute("""
                    INSERT INTO transacciones (user_id, tipo, descripcion)
                    VALUES ($1, $2, $3)
                """, user_id, 'USO_PRODUCTO', f'Uso de producto: {producto_nombre}')
                
                return True, str(role_id) if role_id else None
                
            except Exception as e:
                return False, f"Error al usar producto: {str(e)}"

async def add_product(nombre: str, precio: Decimal, cantidad: int, role_id: int = None) -> bool:
    """Agrega un producto a la tienda"""
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO productos (nombre, precio, cantidad, role_id)
                VALUES ($1, $2, $3, $4)
            """, nombre, float(precio), cantidad, role_id)
            return True
        except asyncpg.UniqueViolationError:
            return False

async def get_all_products() -> list:
    """Obtiene todos los productos disponibles"""
    async with pool.acquire() as conn:
        results = await conn.fetch(
            'SELECT nombre, precio, cantidad, role_id FROM productos WHERE cantidad > 0'
        )
        return [(row['nombre'], row['precio'], row['cantidad'], row['role_id']) for row in results]

async def get_product(nombre: str) -> tuple:
    """Obtiene un producto específico"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            'SELECT nombre, precio, cantidad, role_id FROM productos WHERE nombre = $1', 
            nombre
        )
        if result:
            return (result['nombre'], result['precio'], result['cantidad'], result['role_id'])
        return None

async def update_product(nombre: str, nuevo_precio: Decimal = None, nueva_cantidad: int = None) -> bool:
    """Actualiza un producto"""
    async with pool.acquire() as conn:
        if nuevo_precio is not None and nueva_cantidad is not None:
            result = await conn.execute(
                'UPDATE productos SET precio = $1, cantidad = $2 WHERE nombre = $3', 
                float(nuevo_precio), nueva_cantidad, nombre
            )
        elif nuevo_precio is not None:
            result = await conn.execute(
                'UPDATE productos SET precio = $1 WHERE nombre = $2', 
                float(nuevo_precio), nombre
            )
        elif nueva_cantidad is not None:
            result = await conn.execute(
                'UPDATE productos SET cantidad = $1 WHERE nombre = $2', 
                nueva_cantidad, nombre
            )
        else:
            return False
        
        return result.split()[-1] != '0'  # Verifica si se actualizó alguna fila

async def delete_product(nombre: str) -> bool:
    """Elimina un producto"""
    async with pool.acquire() as conn:
        result = await conn.execute('DELETE FROM productos WHERE nombre = $1', nombre)
        return result.split()[-1] != '0'  # Verifica si se eliminó alguna fila

async def purchase_product(user_id: int, producto_nombre: str, precio: Decimal) -> tuple[bool, str]:
    """Procesa la compra de un producto"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                # Verificar y actualizar stock
                result = await conn.fetchrow(
                    'SELECT cantidad FROM productos WHERE nombre = $1', 
                    producto_nombre
                )
                
                if not result or result['cantidad'] <= 0:
                    return False, "Producto sin stock"
                
                # Reducir stock
                nueva_cantidad = result['cantidad'] - 1
                await conn.execute(
                    'UPDATE productos SET cantidad = $1 WHERE nombre = $2', 
                    nueva_cantidad, producto_nombre
                )
                
                # Actualizar saldo del usuario
                saldo_result = await conn.fetchrow(
                    'SELECT saldo FROM usuarios WHERE user_id = $1', user_id
                )
                saldo_actual = saldo_result['saldo']
                nuevo_saldo = float(saldo_actual) - float(precio)
                
                await conn.execute(
                    'UPDATE usuarios SET saldo = $1 WHERE user_id = $2', 
                    nuevo_saldo, user_id
                )
                
                # Agregar al inventario
                await conn.execute("""
                    INSERT INTO inventario (user_id, producto_nombre, precio_compra)
                    VALUES ($1, $2, $3)
                """, user_id, producto_nombre, float(precio))
                
                # Registrar transacción
                await conn.execute("""
                    INSERT INTO transacciones (user_id, tipo, monto, descripcion)
                    VALUES ($1, $2, $3, $4)
                """, user_id, 'COMPRA', float(precio), f'Compra: {producto_nombre}')
                
                return True, "Compra exitosa"
                
            except Exception as e:
                return False, f"Error en la compra: {str(e)}"

async def get_user_inventory(user_id: int) -> list:
    """Obtiene el inventario de un usuario"""
    async with pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT i.producto_nombre, COUNT(*) as cantidad, AVG(i.precio_compra) as precio_promedio, p.role_id
            FROM inventario i
            LEFT JOIN productos p ON i.producto_nombre = p.nombre
            WHERE i.user_id = $1 
            GROUP BY i.producto_nombre, p.role_id
            ORDER BY MIN(i.fecha_compra) DESC
        """, user_id)
        
        return [(row['producto_nombre'], row['cantidad'], 
                row['precio_promedio'], row['role_id']) for row in results]

async def get_economia_stats() -> dict:
    """Obtiene estadísticas generales del sistema económico"""
    async with pool.acquire() as conn:
        # Total de dinero en circulación
        result = await conn.fetchrow('SELECT SUM(saldo) as total FROM usuarios')
        total_dinero = float(result['total']) if result['total'] else 0
        
        # Número de usuarios con saldo
        result = await conn.fetchrow('SELECT COUNT(*) as count FROM usuarios WHERE saldo > 0')
        usuarios_con_saldo = result['count'] if result else 0
        
        # Total de usuarios registrados
        result = await conn.fetchrow('SELECT COUNT(*) as count FROM usuarios')
        total_usuarios = result['count'] if result else 0
        
        # Productos en tienda
        result = await conn.fetchrow('SELECT COUNT(*) as count FROM productos')
        total_productos = result['count'] if result else 0
        
        # Valor total del inventario en tienda
        result = await conn.fetchrow('SELECT SUM(precio * cantidad) as total FROM productos')
        valor_tienda = float(result['total']) if result['total'] else 0
        
        # Transacciones del día
        result = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM transacciones 
            WHERE DATE(timestamp) = CURRENT_DATE
        """)
        transacciones_hoy = result['count'] if result else 0
        
        return {
            'total_dinero': total_dinero,
            'usuarios_con_saldo': usuarios_con_saldo,
            'total_usuarios': total_usuarios,
            'total_productos': total_productos,
            'valor_tienda': valor_tienda,
            'transacciones_hoy': transacciones_hoy
        }

# ==========================================
# FUNCIONES PARA EL SISTEMA DE INVITACIONES
# ==========================================

async def save_invitation(user_id: int, invited_by_id: int, guild_id: int, invite_code: str = None) -> bool:
    """Guardar invitación en base de datos"""
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO invites (user_id, invited_by_id, guild_id, invite_code, timestamp)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """, user_id, invited_by_id, guild_id, invite_code)
            return True
    except Exception as e:
        print(f"❌ Error guardando invitación: {e}")
        return False

async def get_user_invites_count(user_id: int, guild_id: int) -> int:
    """Obtener conteo de invitaciones activas de un usuario"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM invites 
                WHERE invited_by_id = $1 AND guild_id = $2 AND is_active = TRUE
            """, user_id, guild_id)
            return result['count'] if result else 0
    except Exception as e:
        print(f"❌ Error obteniendo conteo: {e}")
        return 0

async def get_user_inviter(user_id: int, guild_id: int) -> int:
    """Obtener quién invitó a un usuario"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT invited_by_id FROM invites 
                WHERE user_id = $1 AND guild_id = $2
                ORDER BY timestamp DESC LIMIT 1
            """, user_id, guild_id)
            return result['invited_by_id'] if result else None
    except Exception as e:
        print(f"❌ Error obteniendo invitador: {e}")
        return None

async def get_invites_leaderboard(guild_id: int, limit: int = 10) -> list:
    """Obtener leaderboard de invitaciones"""
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT invited_by_id, COUNT(*) as count
                FROM invites 
                WHERE guild_id = $1 AND is_active = TRUE
                GROUP BY invited_by_id
                ORDER BY count DESC
                LIMIT $2
            """, guild_id, limit)
            return [(row['invited_by_id'], row['count']) for row in results]
    except Exception as e:
        print(f"❌ Error obteniendo leaderboard: {e}")
        return []

async def deactivate_user_invites(user_id: int, guild_id: int) -> bool:
    """Marcar invitaciones como inactivas cuando un usuario sale del servidor"""
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE invites SET is_active = FALSE 
                WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)
            return True
    except Exception as e:
        print(f"❌ Error desactivando invitaciones: {e}")
        return False

async def get_invites_stats(guild_id: int) -> dict:
    """Obtener estadísticas del sistema de invitaciones"""
    try:
        async with pool.acquire() as conn:
            # Invitaciones activas
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM invites 
                WHERE guild_id = $1 AND is_active = TRUE
            """, guild_id)
            active_invites = result['count'] if result else 0
            
            # Invitaciones inactivas
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM invites 
                WHERE guild_id = $1 AND is_active = FALSE
            """, guild_id)
            inactive_invites = result['count'] if result else 0
            
            # Usuarios únicos que han invitado
            result = await conn.fetchrow("""
                SELECT COUNT(DISTINCT invited_by_id) as count FROM invites 
                WHERE guild_id = $1 AND is_active = TRUE
            """, guild_id)
            unique_inviters = result['count'] if result else 0
            
            # Mejor invitador
            result = await conn.fetchrow("""
                SELECT invited_by_id, COUNT(*) as count
                FROM invites 
                WHERE guild_id = $1 AND is_active = TRUE
                GROUP BY invited_by_id
                ORDER BY count DESC
                LIMIT 1
            """, guild_id)
            
            top_inviter = None
            top_inviter_count = 0
            if result:
                top_inviter = result['invited_by_id']
                top_inviter_count = result['count']
            
            return {
                'active_invites': active_invites,
                'inactive_invites': inactive_invites,
                'total_invites': active_invites + inactive_invites,
                'unique_inviters': unique_inviters,
                'top_inviter': top_inviter,
                'top_inviter_count': top_inviter_count
            }
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return {
            'active_invites': 0,
            'inactive_invites': 0,
            'total_invites': 0,
            'unique_inviters': 0,
            'top_inviter': None,
            'top_inviter_count': 0
        }

# ==========================================
# FUNCIONES PARA EL SISTEMA DE NIVELES
# ==========================================

async def get_user_level_data(user_id: int, guild_id: int) -> dict:
    """Obtiene los datos de niveles de un usuario"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT * FROM levels_users WHERE user_id = $1 AND guild_id = $2
        """, user_id, guild_id)
        
        if result:
            return dict(result)
        return None

async def update_user_xp(user_id: int, guild_id: int, xp_gain: int, weekly_xp: int = 0, monthly_xp: int = 0):
    """Actualiza la XP de un usuario"""
    import time
    current_time = int(time.time())
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO levels_users (
                user_id, guild_id, xp, level, last_xp_time, total_messages, 
                weekly_xp, monthly_xp, badges, join_date, voice_time
            ) VALUES ($1, $2, $3, 1, $4, 1, $5, $6, '[]'::jsonb, $7, 0)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET 
                xp = levels_users.xp + $3,
                last_xp_time = $4,
                total_messages = levels_users.total_messages + 1,
                weekly_xp = levels_users.weekly_xp + $5,
                monthly_xp = levels_users.monthly_xp + $6
        """, user_id, guild_id, xp_gain, current_time, weekly_xp, monthly_xp, current_time)

async def set_user_xp(user_id: int, guild_id: int, xp: int):
    """Establece la XP exacta de un usuario"""
    import time
    current_time = int(time.time())
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO levels_users (user_id, guild_id, xp, level, join_date)
            VALUES ($1, $2, $3, 1, $4)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET xp = $3, level = 1
        """, user_id, guild_id, xp, current_time)

async def update_user_level(user_id: int, guild_id: int, level: int):
    """Actualiza el nivel de un usuario"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE levels_users SET level = $1 WHERE user_id = $2 AND guild_id = $3
        """, level, user_id, guild_id)

async def get_levels_leaderboard(guild_id: int, limit: int = 10, leaderboard_type: str = 'total') -> list:
    """Obtiene el leaderboard del servidor"""
    async with pool.acquire() as conn:
        if leaderboard_type == 'weekly':
            order_by = 'weekly_xp'
        elif leaderboard_type == 'monthly':
            order_by = 'monthly_xp'
        elif leaderboard_type == 'messages':
            order_by = 'total_messages'
        elif leaderboard_type == 'voice':
            order_by = 'voice_time'
        else:
            order_by = 'xp'
        
        results = await conn.fetch(f"""
            SELECT user_id, xp, level, {order_by}, total_messages, voice_time 
            FROM levels_users 
            WHERE guild_id = $1 AND {order_by} > 0
            ORDER BY {order_by} DESC, level DESC 
            LIMIT $2
        """, guild_id, limit)
        
        return [(row['user_id'], row['xp'], row['level'], row[order_by], 
                row['total_messages'], row['voice_time']) for row in results]

async def get_user_rank(user_id: int, guild_id: int, rank_type: str = 'total') -> int:
    """Obtiene el ranking de un usuario específico"""
    async with pool.acquire() as conn:
        if rank_type == 'weekly':
            order_by = 'weekly_xp'
        elif rank_type == 'monthly':
            order_by = 'monthly_xp'
        else:
            order_by = 'xp'
        
        result = await conn.fetchrow(f"""
            SELECT COUNT(*) + 1 as rank FROM levels_users 
            WHERE guild_id = $1 AND {order_by} > (
                SELECT {order_by} FROM levels_users WHERE user_id = $2 AND guild_id = $3
            )
        """, guild_id, user_id, guild_id)
        
        return result['rank'] if result else 1

async def get_guild_level_config(guild_id: int) -> dict:
    """Obtiene la configuración del servidor para niveles"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow('SELECT * FROM guild_config WHERE guild_id = $1', guild_id)
        
        if result:
            config = dict(result)
            # Convertir campos JSON
            config['enabled_channels'] = config['enabled_channels'] if config['enabled_channels'] else []
            config['disabled_channels'] = config['disabled_channels'] if config['disabled_channels'] else []
            config['bonus_roles'] = config['bonus_roles'] if config['bonus_roles'] else []
            config['custom_rewards'] = config['custom_rewards'] if config['custom_rewards'] else {}
            return config
        
        return {
            'guild_id': guild_id,
            'level_up_channel': None,
            'xp_per_message': 15,
            'xp_cooldown': 60,
            'enabled_channels': [],
            'disabled_channels': [],
            'xp_multiplier': 1.0,
            'level_formula': 'exponential',
            'voice_xp_enabled': False,
            'voice_xp_rate': 5,
            'bonus_roles': [],
            'announce_level_up': True,
            'stack_roles': False,
            'custom_rewards': {}
        }

async def set_level_role(guild_id: int, level: int, role_id: int):
    """Configura un rol para un nivel específico"""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO level_roles (guild_id, level, role_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, level) 
            DO UPDATE SET role_id = $3
        """, guild_id, level, role_id)

async def remove_level_role(guild_id: int, level: int):
    """Elimina un rol de nivel"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM level_roles WHERE guild_id = $1 AND level = $2', guild_id, level)

async def get_level_roles(guild_id: int) -> dict:
    """Obtiene todos los roles configurados por nivel"""
    async with pool.acquire() as conn:
        results = await conn.fetch('SELECT level, role_id FROM level_roles WHERE guild_id = $1 ORDER BY level', guild_id)
        return {row['level']: row['role_id'] for row in results}

async def add_badge(user_id: int, guild_id: int, badge_id: str) -> bool:
    """Agrega una insignia a un usuario"""
    async with pool.acquire() as conn:
        user_data = await get_user_level_data(user_id, guild_id)
        if not user_data:
            return False
        
        badges = user_data['badges'] if user_data['badges'] else []
        if badge_id not in badges:
            badges.append(badge_id)
            
            await conn.execute(
                'UPDATE levels_users SET badges = $1 WHERE user_id = $2 AND guild_id = $3',
                json.dumps(badges), user_id, guild_id
            )
            return True
        return False

async def get_level_server_stats(guild_id: int) -> dict:
    """Obtiene estadísticas del servidor para niveles"""
    async with pool.acquire() as conn:
        # Contar usuarios totales
        result = await conn.fetchrow('SELECT COUNT(*) as count FROM levels_users WHERE guild_id = $1', guild_id)
        total_users = result['count'] if result else 0
        
        # Usuario con más XP
        result = await conn.fetchrow(
            'SELECT user_id, xp, level FROM levels_users WHERE guild_id = $1 ORDER BY xp DESC LIMIT 1', 
            guild_id
        )
        top_user = (result['user_id'], result['xp'], result['level']) if result else None
        
        # Nivel promedio
        result = await conn.fetchrow('SELECT AVG(level) as avg_level FROM levels_users WHERE guild_id = $1', guild_id)
        avg_level = float(result['avg_level']) if result['avg_level'] else 0
        
        # Total de mensajes
        result = await conn.fetchrow('SELECT SUM(total_messages) as total FROM levels_users WHERE guild_id = $1', guild_id)
        total_messages = result['total'] if result else 0
        
        # Usuarios por nivel
        results = await conn.fetch(
            'SELECT level, COUNT(*) as count FROM levels_users WHERE guild_id = $1 GROUP BY level ORDER BY level', 
            guild_id
        )
        level_distribution = {row['level']: row['count'] for row in results}
        
        return {
            'total_users': total_users,
            'top_user': top_user,
            'avg_level': avg_level,
            'total_messages': total_messages,
            'level_distribution': level_distribution
        }

async def update_guild_config(guild_id: int, **kwargs):
    """Actualiza la configuración de un servidor"""
    async with pool.acquire() as conn:
        # Primero insertar configuración base si no existe
        await conn.execute("""
            INSERT INTO guild_config (guild_id) VALUES ($1)
            ON CONFLICT (guild_id) DO NOTHING
        """, guild_id)
        
        # Actualizar campos específicos
        for field, value in kwargs.items():
            if field in ['enabled_channels', 'disabled_channels', 'bonus_roles', 'custom_rewards']:
                # Campos JSON
                await conn.execute(f"""
                    UPDATE guild_config SET {field} = $1 WHERE guild_id = $2
                """, json.dumps(value), guild_id)
            else:
                # Campos regulares
                await conn.execute(f"""
                    UPDATE guild_config SET {field} = $1 WHERE guild_id = $2
                """, value, guild_id)

async def reset_weekly_xp(guild_id: int = None):
    """Resetea la XP semanal"""
    async with pool.acquire() as conn:
        if guild_id:
            await conn.execute('UPDATE levels_users SET weekly_xp = 0 WHERE guild_id = $1', guild_id)
        else:
            await conn.execute('UPDATE levels_users SET weekly_xp = 0')

async def reset_monthly_xp(guild_id: int = None):
    """Resetea la XP mensual"""
    async with pool.acquire() as conn:
        if guild_id:
            await conn.execute('UPDATE levels_users SET monthly_xp = 0 WHERE guild_id = $1', guild_id)
        else:
            await conn.execute('UPDATE levels_users SET monthly_xp = 0')