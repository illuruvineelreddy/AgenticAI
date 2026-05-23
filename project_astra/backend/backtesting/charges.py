"""
Indian Equity Brokerage and Transaction Charges Calculator
Calculates all transaction costs for NSE Equity intraday and delivery trades.
"""

from typing import Dict

class IndianBrokerageCalculator:
    """
    Calculates charges for Indian equity trades.
    Matches standard discount broker (e.g., Zerodha) pricing model.
    """
    
    # Pricing constants
    BROKERAGE_PCT = 0.0003  # 0.03%
    MAX_BROKERAGE_PER_ORDER = 20.0  # ₹20 flat max
    
    # Securities Transaction Tax (STT)
    STT_INTRADAY_SELL = 0.00025  # 0.025% on sell side only
    STT_DELIVERY_BUY = 0.001     # 0.1% on buy
    STT_DELIVERY_SELL = 0.001    # 0.1% on sell
    
    # Exchange Transaction Charges (NSE)
    EXCHANGE_TXN_CHARGE = 0.0000325  # 0.00325% on buy & sell
    
    # SEBI Turnover Fee
    SEBI_FEE = 0.0000001  # ₹10 per crore (0.00001%)
    
    # GST
    GST_RATE = 0.18  # 18% on (Brokerage + Exchange Txn Charge + SEBI Fee)
    
    # Stamp Duty (applicable on Buy side only)
    STAMP_DUTY_INTRADAY = 0.00003  # 0.003% on buy
    STAMP_DUTY_DELIVERY = 0.00015  # 0.015% on buy
    
    @classmethod
    def calculate_charges(cls, quantity: int, price: float, side: str, is_delivery: bool = False) -> Dict[str, float]:
        """
        Calculates detailed transaction charges for a single order fill.
        """
        trade_value = quantity * price
        side = side.upper()
        
        # 1. Brokerage
        raw_brokerage = trade_value * cls.BROKERAGE_PCT if is_delivery else trade_value * cls.BROKERAGE_PCT
        if is_delivery:
            # Many discount brokers offer ₹0 brokerage on delivery, but let's assume flat max or 0
            brokerage = 0.0
        else:
            brokerage = min(raw_brokerage, cls.MAX_BROKERAGE_PER_ORDER)

        # 2. STT
        stt = 0.0
        if is_delivery:
            stt = trade_value * cls.STT_DELIVERY_BUY if side == 'BUY' else trade_value * cls.STT_DELIVERY_SELL
        else:
            stt = trade_value * cls.STT_INTRADAY_SELL if side == 'SELL' else 0.0
            
        # 3. Exchange Transaction Charge
        exchange_charge = trade_value * cls.EXCHANGE_TXN_CHARGE
        
        # 4. SEBI Fee
        sebi_fee = trade_value * cls.SEBI_FEE
        
        # 5. GST
        gst = (brokerage + exchange_charge + sebi_fee) * cls.GST_RATE
        
        # 6. Stamp Duty (Buy side only)
        stamp_duty = 0.0
        if side == 'BUY':
            stamp_duty = trade_value * cls.STAMP_DUTY_DELIVERY if is_delivery else trade_value * cls.STAMP_DUTY_INTRADAY
            
        total_charges = brokerage + stt + exchange_charge + sebi_fee + gst + stamp_duty
        
        return {
            'trade_value': float(trade_value),
            'brokerage': float(brokerage),
            'stt': float(stt),
            'exchange_charges': float(exchange_charge),
            'sebi_turnover_fee': float(sebi_fee),
            'gst': float(gst),
            'stamp_duty': float(stamp_duty),
            'total_charges': float(total_charges)
        }
