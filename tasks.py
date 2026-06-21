import asyncio
import logging
import aiohttp
import config
from database.sqlite import (
    get_stale_crypto_invoices,
    get_stale_clone_crypto_invoices,
    update_crypto_invoice_status,
    update_clone_invoice_status
)

logger = logging.getLogger(__name__)

async def cancel_invoice_on_api(session: aiohttp.ClientSession, invoice_id: str) -> bool:
    """Attempts to cancel the invoice on the BSC gateway. Returns True on success."""
    headers = {"x-api-key": config.BSC_API_KEY}
    try:
        async with session.post(f"https://bscusdtapi.onrender.com/api/invoices/{invoice_id}/cancel", headers=headers) as resp:
            # We don't strictly care about the status, but logging it is useful
            if resp.status not in [200, 201, 400, 404]:
                logger.warning(f"Unexpected status from BSC API when cancelling invoice {invoice_id}: {resp.status}")
            return True
    except Exception as e:
        logger.error(f"Failed to cancel invoice {invoice_id} on API: {e}")
        return False

async def cleanup_stale_invoices_loop():
    """
    Background loop that runs continuously.
    Every 1 hour, it finds invoices older than 12 hours and cancels them slowly (1 by 1).
    """
    logger.info("Invoice cleanup background task started.")
    
    while True:
        try:
            stale_main_invoices = get_stale_crypto_invoices(hours=12)
            stale_clone_invoices = get_stale_clone_crypto_invoices(hours=12)
            
            total_stale = len(stale_main_invoices) + len(stale_clone_invoices)
            if total_stale > 0:
                logger.info(f"Found {total_stale} stale invoices. Beginning cleanup...")
                
                async with aiohttp.ClientSession() as session:
                    # Clean up main bot invoices
                    for invoice_id in stale_main_invoices:
                        logger.info(f"Cancelling stale main invoice: {invoice_id}")
                        await cancel_invoice_on_api(session, invoice_id)
                        update_crypto_invoice_status(invoice_id, "canceled")
                        await asyncio.sleep(5) # Delay 5 seconds between cancellations
                    
                    # Clean up clone bot invoices
                    for invoice_id in stale_clone_invoices:
                        logger.info(f"Cancelling stale clone invoice: {invoice_id}")
                        await cancel_invoice_on_api(session, invoice_id)
                        update_clone_invoice_status(invoice_id, "canceled")
                        await asyncio.sleep(5) # Delay 5 seconds between cancellations
                        
                logger.info("Stale invoice cleanup completed.")
                
        except Exception as e:
            logger.error(f"Error in invoice cleanup loop: {e}")
            
        # Sleep for 1 hour before checking again
        await asyncio.sleep(3600)
