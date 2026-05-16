async def handle_subscription(request):
    sub_key = request.match_info.get('key')
    user = await database.get_user_by_sub_key(sub_key)
    
    if not user:
        return web.Response(text='Invalid subscription', status=403)
    
    # Формируем конфиг для Happy Plus / v2rayNG
    config = f"""proxies:
  - name: ULTROvpn
    type: vmess
    server: {config.SERVER_HOST}
    port: {config.SERVER_PORT}
    uuid: {user.get('vmess_id', '12345678-1234-1234-1234-123456789012')}
    alterId: 0
    cipher: auto
    tls: false
    network: tcp
"""
    return web.Response(text=config, content_type='text/plain')

# Добавьте маршрут (в конец файла, перед web.run_app)
app.router.add_get('/sub/{key}', handle_subscription)
