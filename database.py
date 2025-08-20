import os
import asyncpg
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

DB_URL = os.getenv("DATABASE_URL")

pool = None

async def create_pool():
    return await asyncpg.create_pool(DB_URL, ssl="require")

async def connect_db():
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
            -- columnas nuevas para leaderboards
            weekly_xp BIGINT DEFAULT 0,
            monthly_xp BIGINT DEFAULT 0,
            weekly_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            monthly_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

        # === TABLAS DEL SISTEMA DE PARTNERS ===
        
        # Tabla para partners
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS partners (
            id SERIAL PRIMARY KEY,
            author_id BIGINT NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Tabla para configuración del contador de partners
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS partner_config (
            key TEXT PRIMARY KEY,
            value INTEGER
        );
        """)
        
        # Inicializar contador si no existe
        await conn.execute("""
        INSERT INTO partner_config (key, value) 
        VALUES ('partner_count', 0) 
        ON CONFLICT (key) DO NOTHING;
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
        
        # Índices para el sistema de partners
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_partners_author_id ON partners(author_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_partners_created_at ON partners(created_at DESC)')

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

def get_monday_of_week():
    """Obtiene el lunes de la semana actual en horario de España (UTC+1) - SIN timezone info para PostgreSQL"""
    from datetime import datetime, timedelta, timezone
    
    # Horario de España (UTC+1)
    spain_tz = timezone(timedelta(hours=1))
    now = datetime.now(spain_tz)
    
    # Obtener el lunes de esta semana
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # IMPORTANTE: Remover timezone info para PostgreSQL TIMESTAMP
    return monday.replace(tzinfo=None)

def get_first_of_month():
    """Obtiene el primer día del mes actual en horario de España (UTC+1) - SIN timezone info para PostgreSQL"""
    from datetime import datetime, timedelta, timezone
    
    # Horario de España (UTC+1)
    spain_tz = timezone(timedelta(hours=1))
    now = datetime.now(spain_tz)
    
    # Primer día del mes
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # IMPORTANTE: Remover timezone info para PostgreSQL TIMESTAMP
    return first_day.replace(tzinfo=None)

async def update_user_xp(user_id: int, guild_id: int, xp_gain: int, weekly_xp: int = 0, monthly_xp: int = 0):
    """Actualiza la XP de un usuario - VERSIÓN CORREGIDA que siempre crea el usuario si no existe"""
    import time
    current_time = int(time.time())
    monday = get_monday_of_week()
    first_day = get_first_of_month()
    
    async with pool.acquire() as conn:
        try:
            # Intentar obtener el usuario actual primero
            existing_user = await conn.fetchrow("""
                SELECT xp, weekly_xp, monthly_xp, weekly_reset, monthly_reset 
                FROM levels_users 
                WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)
            
            if existing_user:
                # Usuario existe, actualizar
                current_xp = existing_user['xp']
                current_weekly_xp = existing_user['weekly_xp']
                current_monthly_xp = existing_user['monthly_xp']
                weekly_reset = existing_user['weekly_reset']
                monthly_reset = existing_user['monthly_reset']
                
                # Verificar si necesita reset semanal (comparar datetime sin timezone)
                if weekly_reset is None or weekly_reset < monday:
                    new_weekly_xp = weekly_xp  # Resetear XP semanal
                    weekly_reset_to_use = monday
                else:
                    new_weekly_xp = current_weekly_xp + weekly_xp
                    weekly_reset_to_use = weekly_reset
                
                # Verificar si necesita reset mensual (comparar datetime sin timezone)
                if monthly_reset is None or monthly_reset < first_day:
                    new_monthly_xp = monthly_xp  # Resetear XP mensual
                    monthly_reset_to_use = first_day
                else:
                    new_monthly_xp = current_monthly_xp + monthly_xp
                    monthly_reset_to_use = monthly_reset
                
                # Actualizar usuario existente
                await conn.execute("""
                    UPDATE levels_users SET 
                        xp = $1,
                        last_xp_time = $2,
                        total_messages = total_messages + 1,
                        weekly_xp = $3,
                        monthly_xp = $4,
                        weekly_reset = $5,
                        monthly_reset = $6
                    WHERE user_id = $7 AND guild_id = $8
                """, current_xp + xp_gain, current_time, new_weekly_xp, new_monthly_xp, 
                    weekly_reset_to_use, monthly_reset_to_use, user_id, guild_id)
                
            else:
                # Usuario no existe, crear nuevo registro
                await conn.execute("""
                    INSERT INTO levels_users (
                        user_id, guild_id, xp, level, last_xp_time, total_messages, 
                        weekly_xp, monthly_xp, badges, join_date, voice_time, 
                        weekly_reset, monthly_reset
                    ) VALUES ($1, $2, $3, 1, $4, 1, $5, $6, '[]'::jsonb, $7, 0, $8, $9)
                """, user_id, guild_id, xp_gain, current_time, weekly_xp, monthly_xp, 
                    current_time, monday, first_day)
                
        except Exception as e:
            print(f"Error en update_user_xp: {e}")
            raise e

async def ensure_user_exists(user_id: int, guild_id: int):
    """Asegura que un usuario existe en la base de datos, creándolo si es necesario"""
    import time
    current_time = int(time.time())
    monday = get_monday_of_week()
    first_day = get_first_of_month()
    
    async with pool.acquire() as conn:
        try:
            # Verificar si el usuario existe
            existing = await conn.fetchrow("""
                SELECT user_id FROM levels_users WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)
            
            if not existing:
                # Crear usuario nuevo con valores iniciales
                await conn.execute("""
                    INSERT INTO levels_users (
                        user_id, guild_id, xp, level, last_xp_time, total_messages, 
                        weekly_xp, monthly_xp, badges, join_date, voice_time, 
                        weekly_reset, monthly_reset
                    ) VALUES ($1, $2, 0, 1, 0, 0, 0, 0, '[]'::jsonb, $3, 0, $4, $5)
                    ON CONFLICT (user_id, guild_id) DO NOTHING
                """, user_id, guild_id, current_time, monday, first_day)
                
                print(f"Usuario {user_id} creado en guild {guild_id}")
                return True
            return False
            
        except Exception as e:
            print(f"Error en ensure_user_exists: {e}")
            return False

async def get_weekly_leaderboard(guild_id: int, limit: int = 10) -> list:
    """Obtiene el ranking semanal por XP ganada - VERSIÓN MEJORADA"""
    monday = get_monday_of_week()
    
    async with pool.acquire() as conn:
        try:
            results = await conn.fetch("""
                SELECT user_id, 
                       CASE 
                           WHEN weekly_reset IS NULL OR weekly_reset < $2 THEN 0 
                           ELSE weekly_xp 
                       END as weekly_xp
                FROM levels_users 
                WHERE guild_id = $1 AND (
                    (weekly_reset IS NOT NULL AND weekly_reset >= $2 AND weekly_xp > 0) OR
                    (weekly_reset IS NULL OR weekly_reset < $2)
                )
                ORDER BY CASE 
                             WHEN weekly_reset IS NULL OR weekly_reset < $2 THEN 0 
                             ELSE weekly_xp 
                         END DESC
                LIMIT $3
            """, guild_id, monday, limit)
            
            return [{'user_id': row['user_id'], 'xp': row['weekly_xp']} for row in results if row['weekly_xp'] > 0]
            
        except Exception as e:
            print(f"Error en get_weekly_leaderboard: {e}")
            return []

async def get_monthly_leaderboard(guild_id: int, limit: int = 10) -> list:
    """Obtiene el ranking mensual por XP ganada - VERSIÓN MEJORADA"""
    first_day = get_first_of_month()
    
    async with pool.acquire() as conn:
        try:
            results = await conn.fetch("""
                SELECT user_id, 
                       CASE 
                           WHEN monthly_reset IS NULL OR monthly_reset < $2 THEN 0 
                           ELSE monthly_xp 
                       END as monthly_xp
                FROM levels_users 
                WHERE guild_id = $1 AND (
                    (monthly_reset IS NOT NULL AND monthly_reset >= $2 AND monthly_xp > 0) OR
                    (monthly_reset IS NULL OR monthly_reset < $2)
                )
                ORDER BY CASE 
                             WHEN monthly_reset IS NULL OR monthly_reset < $2 THEN 0 
                             ELSE monthly_xp 
                         END DESC
                LIMIT $3
            """, guild_id, first_day, limit)
            
            return [{'user_id': row['user_id'], 'xp': row['monthly_xp']} for row in results if row['monthly_xp'] > 0]
            
        except Exception as e:
            print(f"Error en get_monthly_leaderboard: {e}")
            return []

async def reset_weekly_xp(guild_id: int = None):
    """Resetea la XP semanal"""
    monday = get_monday_of_week()
    
    async with pool.acquire() as conn:
        if guild_id:
            await conn.execute("""
                UPDATE levels_users SET weekly_xp = 0, weekly_reset = $1 
                WHERE guild_id = $2
            """, monday, guild_id)
        else:
            await conn.execute('UPDATE levels_users SET weekly_xp = 0, weekly_reset = $1', monday)

async def reset_monthly_xp(guild_id: int = None):
    """Resetea la XP mensual"""
    first_day = get_first_of_month()
    
    async with pool.acquire() as conn:
        if guild_id:
            await conn.execute("""
                UPDATE levels_users SET monthly_xp = 0, monthly_reset = $1 
                WHERE guild_id = $2
            """, first_day, guild_id)
        else:
            await conn.execute('UPDATE levels_users SET monthly_xp = 0, monthly_reset = $1', first_day)

# ==========================================
# FUNCIONES ADICIONALES PARA EL SISTEMA DE NIVELES
# ==========================================

async def add_user_xp(user_id: int, guild_id: int, xp_amount: int):
    """Agrega XP a un usuario específico"""
    import time
    current_time = int(time.time())
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO levels_users (
                user_id, guild_id, xp, level, last_xp_time, total_messages, 
                weekly_xp, monthly_xp, badges, join_date, voice_time
            ) VALUES ($1, $2, $3, 1, $4, 0, $3, $3, '[]'::jsonb, $4, 0)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET 
                xp = levels_users.xp + $3,
                last_xp_time = $4,
                weekly_xp = levels_users.weekly_xp + $3,
                monthly_xp = levels_users.monthly_xp + $3
        """, user_id, guild_id, xp_amount, current_time)

async def set_user_level(user_id: int, guild_id: int, level: int):
    """Establece el nivel de un usuario (wrapper para compatibilidad)"""
    await update_user_level(user_id, guild_id, level)

# ==========================================
# FUNCIONES PARA EL SISTEMA DE PARTNERS
# ==========================================

async def get_next_partner_number() -> int:
    """Obtiene el siguiente número de partner"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Obtener contador actual
            result = await conn.fetchrow('SELECT value FROM partner_config WHERE key = $1', 'partner_count')
            current = result['value'] if result else 0
            new_count = current + 1
            
            # Actualizar contador
            await conn.execute(
                'UPDATE partner_config SET value = $1 WHERE key = $2', 
                new_count, 'partner_count'
            )
            
            return new_count

async def save_partner(author_id: int, author_name: str, content: str) -> bool:
    """Guarda el partner en la base de datos"""
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO partners (author_id, author_name, content)
                VALUES ($1, $2, $3)
            """, author_id, author_name, content)
            return True
    except Exception as e:
        print(f"Error guardando partner: {e}")
        return False

async def get_partner_stats() -> dict:
    """Obtiene estadísticas de partners"""
    async with pool.acquire() as conn:
        # Total de partners
        result = await conn.fetchrow('SELECT COUNT(*) as total FROM partners')
        total = result['total'] if result else 0
        
        # Partners por usuario (top 5)
        results = await conn.fetch("""
            SELECT author_name, COUNT(*) as count 
            FROM partners 
            GROUP BY author_name, author_id 
            ORDER BY count DESC 
            LIMIT 5
        """)
        
        top_users = [(row['author_name'], row['count']) for row in results]
        
        return {
            'total': total,
            'top_users': top_users
        }

async def get_partners_list(limit: int = 5) -> list:
    """Lista los últimos partners"""
    async with pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT id, author_name, content, created_at 
            FROM partners 
            ORDER BY created_at DESC 
            LIMIT $1
        """, limit)
        
        return [(row['id'], row['author_name'], row['content'], row['created_at']) for row in results]

async def delete_partner(partner_id: int) -> bool:
    """Elimina un partner por ID"""
    try:
        async with pool.acquire() as conn:
            # Verificar que existe
            result = await conn.fetchrow('SELECT id FROM partners WHERE id = $1', partner_id)
            if not result:
                return False
            
            # Eliminar
            await conn.execute('DELETE FROM partners WHERE id = $1', partner_id)
            return True
    except Exception as e:
        print(f"Error eliminando partner: {e}")
        return False

async def get_partner_by_id(partner_id: int) -> tuple:
    """Obtiene un partner específico por ID"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT id, author_name, content, created_at 
            FROM partners WHERE id = $1
        """, partner_id)
        
        if result:
            return (result['id'], result['author_name'], result['content'], result['created_at'])
        return None