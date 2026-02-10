"""
Setup Telegram Bot Webhook
Run this script to configure the Telegram webhook URL
Usage: python setup_telegram_webhook.py <your_domain>
Example: python setup_telegram_webhook.py https://your-domain.com
"""

import requests
import sys

# Telegram Bot Token
BOT_TOKEN = "8182454698:AAHnjMMS8DQ8J39M6rTwmL2qWDisUm5HWPA"

def setup_webhook(domain):
    """
    Setup Telegram webhook to receive updates
    """
    webhook_url = f"{domain}/patient/telegram/webhook/"
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    # Set webhook
    response = requests.post(api_url, json={'url': webhook_url})
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print(f"✅ Webhook set successfully!")
            print(f"Webhook URL: {webhook_url}")
            print(f"Description: {result.get('description', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        return False


def get_webhook_info():
    """
    Get current webhook information
    """
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            info = result.get('result', {})
            print("\n📋 Current Webhook Info:")
            print(f"  URL: {info.get('url', 'Not set')}")
            print(f"  Pending updates: {info.get('pending_update_count', 0)}")
            print(f"  Last error: {info.get('last_error_message', 'None')}")
            return info
    return None


def delete_webhook():
    """
    Delete the webhook (useful for local testing)
    """
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.post(api_url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print("✅ Webhook deleted successfully!")
            print("Bot will now work in polling mode for local testing")
            return True
    print("❌ Failed to delete webhook")
    return False


def get_bot_info():
    """
    Get bot information
    """
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            bot = result.get('result', {})
            print("\n🤖 Bot Information:")
            print(f"  Name: {bot.get('first_name', 'N/A')}")
            print(f"  Username: @{bot.get('username', 'N/A')}")
            print(f"  ID: {bot.get('id', 'N/A')}")
            print(f"  Can join groups: {bot.get('can_join_groups', False)}")
            print(f"  Can read messages: {bot.get('can_read_all_group_messages', False)}")
            return bot
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Bot Webhook Setup")
    print("=" * 60)
    
    # Get bot info
    bot_info = get_bot_info()
    
    # Get current webhook status
    get_webhook_info()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['delete', 'remove', 'clear']:
            # Delete webhook
            delete_webhook()
        elif command.startswith('http'):
            # Set webhook
            domain = sys.argv[1].rstrip('/')
            setup_webhook(domain)
        else:
            print("\n❌ Invalid command!")
            print("\nUsage:")
            print("  Setup webhook:  python setup_telegram_webhook.py https://your-domain.com")
            print("  Delete webhook: python setup_telegram_webhook.py delete")
            print("  Get info:       python setup_telegram_webhook.py")
    else:
        print("\n💡 To set up webhook, run:")
        print("   python setup_telegram_webhook.py https://your-domain.com")
        print("\n💡 For local testing (delete webhook), run:")
        print("   python setup_telegram_webhook.py delete")
        
        if bot_info:
            bot_username = bot_info.get('username', 'N/A')
            print(f"\n📱 Bot Link: https://t.me/{bot_username}")
            print(f"   Users can start chat with: https://t.me/{bot_username}?start=USERNAME")
    
    print("\n" + "=" * 60)
