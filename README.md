# Alquimia Dulce

Proyecto con un backend Django REST conectado a PostgreSQL de Supabase y un frontend React construido con Vite y Tailwind CSS.

## Requisitos

- Python 3.14 o compatible con Django 6.1
- Node.js 20.19+ o 22.12+
- Una base de datos PostgreSQL de Supabase

## Backend

1. Crea y activa un entorno virtual dentro de `backend/`.
2. Instala las dependencias: `pip install -r requirements.txt`.
3. Copia `backend/.env.example` a `backend/.env` y completa los valores reales.
4. Ejecuta las migraciones: `python manage.py migrate`.
5. Inicia el servidor: `python manage.py runserver`.

El estado del backend está disponible en `http://localhost:8000/api/health/`.

## API inicial

La API se publica bajo `http://localhost:8000/api/v1/`.

- `POST /auth/register/`: crea una cuenta con correo y contrasena.
- `POST /auth/token/`: devuelve tokens JWT `access` y `refresh`.
- `POST /auth/token/refresh/`: renueva un token de acceso.
- `GET` y `PATCH /auth/profile/`: consulta o actualiza el perfil autenticado.
- `GET`, `POST`, `PATCH` y `DELETE /auth/addresses/`: administra las direcciones propias.
- `GET /categories/`: lista las categorias activas.
- `GET /products/`: lista productos disponibles.
- `GET /products/{slug}/`: devuelve el detalle de un producto.
- `GET /cart/`: obtiene el carrito persistente del consumidor autenticado.
- `POST /cart/items/`: agrega una variante al carrito.
- `PATCH` y `DELETE /cart/items/{id}/`: actualiza cantidad o elimina un item.
- `DELETE /cart/`: vacia el carrito.
- `GET /availability/?date=YYYY-MM-DD`: consulta cupo y franjas disponibles.
- `POST /orders/checkout/`: crea un pedido desde el carrito autenticado.
- `GET /orders/` y `GET /orders/{code}/`: consulta los pedidos propios.
- `POST /orders/{code}/payment-preference/`: crea o reutiliza la preferencia de Mercado Pago para un pedido reservado.
- `POST /payments/mercado-pago/webhook/`: recibe eventos de pago de Mercado Pago.
- `GET` y `POST /custom-orders/`: consulta o crea solicitudes personalizadas propias.
- `GET /custom-orders/{id}/`: consulta una solicitud personalizada propia.
- `POST /custom-orders/{id}/accept/`: acepta una cotizacion vigente y crea el pedido reservado.
- `GET /admin/custom-orders/`: lista solicitudes para administradores.
- `POST /admin/custom-orders/{id}/quote/`: crea o actualiza una cotizacion administrativa.
- `POST /admin/custom-orders/{id}/reject/`: rechaza una solicitud administrativa.

El catalogo acepta los parametros opcionales `category`, `search`, `featured=true` e `in_stock=true`. Los importes de variantes se expresan en centimos: `5500` representa `S/ 55.00`.

El checkout recalcula precios en el backend, aplica `S/ 10.00` para delivery, descuenta stock y reserva stock/cupo por 15 minutos. Programa `python manage.py expire_pending_orders` cada minuto en el entorno de despliegue para cancelar reservas vencidas y restaurar el inventario.

Las solicitudes personalizadas admiten retiro o delivery, imagen de referencia, sabor, porciones, tematica y mensaje. El administrador cotiza el importe total, fecha, franja y vigencia. Al aceptarla, se crea un pedido pendiente de pago; el webhook aprobado lo marca como convertido.

## Mercado Pago

La integracion esta preparada para Mercado Pago Checkout Pro y usa `PEN`. Mientras no existan credenciales, el endpoint de preferencia responde con un error claro y no realiza llamadas externas.

Para activarla, completa estas variables en `backend/.env`:

- `MERCADO_PAGO_ACCESS_TOKEN`
- `MERCADO_PAGO_WEBHOOK_SECRET`
- `MERCADO_PAGO_SUCCESS_URL`
- `MERCADO_PAGO_FAILURE_URL`
- `MERCADO_PAGO_PENDING_URL`
- `MERCADO_PAGO_NOTIFICATION_URL`

El frontend debe redirigir al consumidor a `checkout_url` devuelto por la preferencia. Los retornos del navegador no confirman una compra: solo el webhook valida el pago con la API de Mercado Pago, comprueba monto, moneda y pedido, y cambia el pedido a `paid`.

## Arquitectura del backend

El backend se organiza por dominios dentro de `backend/apps/`:

- `accounts`: usuario autenticado por correo y direcciones de entrega.
- `catalog`: categorias, productos, tamanos, stock e imagenes.
- `cart`: carritos e items.
- `orders`: pedidos, disponibilidad, feriados y franjas horarias.
- `custom_orders`: solicitudes y cotizaciones de pedidos personalizados.
- `payments`: pagos de Mercado Pago.

Las migraciones iniciales crean la configuracion operativa de Alquimia Dulce:

- Delivery fijo de `S/ 10.00`.
- Retiro en Villa El Salvador.
- Capacidad maxima de 20 pedidos por dia.
- Franjas: 09:00-12:00, 12:00-15:00, 15:00-18:00 y 18:00-21:00.
- Zona horaria `America/Lima`.

Ejecuta las pruebas del backend con `python manage.py test` desde `backend/`.

## Frontend

1. Entra en `frontend/` e instala dependencias: `npm install`.
2. Opcionalmente copia `.env.example` a `.env` y define `VITE_API_BASE_URL`.
3. Inicia Vite: `npm run dev`.

El origen de desarrollo `http://localhost:5173` está permitido por defecto mediante CORS. Para otros dominios, actualiza `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` en `backend/.env`.

## Seguridad

- Nunca subas `backend/.env` ni credenciales al repositorio.
- Usa una `DJANGO_SECRET_KEY` distinta y aleatoria por entorno.
- En producción configura `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` con los dominios públicos y orígenes HTTPS explícitos para CORS y CSRF.
- La contraseña de Supabase que ya estuvo versionada debe rotarse desde el panel de Supabase antes de desplegar.
