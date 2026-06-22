import os

locales_dir = 'locales'
for file in os.listdir(locales_dir):
    if not file.endswith('.py') or file == '__init__.py':
        continue
    filepath = os.path.join(locales_dir, file)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace TABLE_USDT = "USDT" with "USDT (BEP20)"
    content = content.replace('TABLE_USDT = "USDT"', 'TABLE_USDT = "USDT (BEP20)"')
    
    # Replace the button text manually
    content = content.replace('🪙 Pay {usdt} USDT"', '🪙 Pay {usdt} USDT (BEP20)"')
    content = content.replace('🪙 Оплатить {usdt} USDT"', '🪙 Оплатить {usdt} USDT (BEP20)"')
    content = content.replace('🪙 Оплатити {usdt} USDT"', '🪙 Оплатити {usdt} USDT (BEP20)"')
    content = content.replace('🪙 支付 {usdt} USDT"', '🪙 支付 {usdt} USDT (BEP20)"')
    content = content.replace('🪙 {usdt} USDT से भुगतान करें"', '🪙 {usdt} USDT (BEP20) से भुगतान करें"')
    content = content.replace('🪙 الدفع بـ {usdt} USDT"', '🪙 الدفع بـ {usdt} USDT (BEP20)"')
    content = content.replace('🪙 {usdt} USDT سے ادا کریں"', '🪙 {usdt} USDT (BEP20) سے ادا کریں"')
    content = content.replace('🪙 {usdt} USDT দিয়ে পেমেন্ট করুন"', '🪙 {usdt} USDT (BEP20) দিয়ে পেমেন্ট করুন"')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done")
