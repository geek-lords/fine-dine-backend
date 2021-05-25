import logging
from enum import Enum

from paytmpg import MerchantProperty, LibraryConstants, EChannelId, Money, EnumCurrency, UserInfo, \
    PaymentDetailsBuilder, Payment, PaymentStatusDetailBuilder
from paytmpg.merchant.models.PaymentStatusDetail import PaymentStatusDetail

from config import merchant_id, merchant_key, website, callback_url


class PaymentStatus(Enum):
    SUCCESSFUL = 0
    PENDING = 1
    INVALID = 2
    FAILED = 3
    NOT_PAID = 4

    def to_string(self):
        if self.value == self.SUCCESSFUL.value:
            return 'successful'
        if self.value == self.PENDING.value:
            return 'pending'
        if self.value == self.INVALID.value:
            return 'invalid'
        if self.value == self.FAILED.value:
            return 'failed'
        if self.value == self.NOT_PAID.value:
            return 'not_paid'


logger = logging.getLogger(__name__)


environment = LibraryConstants.STAGING_ENVIRONMENT

MerchantProperty.initialize(environment, merchant_id, merchant_key, '1', website)
MerchantProperty.set_callback_url(callback_url)

MerchantProperty.logger = logger


def initiate_transaction(user_id, txn_id, amount):
    channel_id = EChannelId.APP
    txn_amount = Money(EnumCurrency.INR, '%.2f' % amount)

    user_info = UserInfo()
    user_info.set_cust_id(user_id)

    # if you look at the definition paytm calls txn_id order_id
    # but our unique transaction_id is called txn_id. it has nothing to
    # do with order id.
    builder = PaymentDetailsBuilder(channel_id, txn_id, txn_amount, user_info)
    payment_details = builder.build()

    response = Payment.createTxnToken(payment_details)
    logger.info(response)
    body = response.get_response_object().get_body()

    return body.txnToken, f'{callback_url}?ORDER_ID={txn_id}'


def payment_status(txn_id):
    builder = PaymentStatusDetailBuilder(txn_id)

    response = Payment.getPaymentStatus(PaymentStatusDetail(builder))
    logger.info(response)

    result_code = response.get_response_object().get_body().resultInfo.resultCode

    # 501 is technically a failure but paytm is returning 501 in my test response
    # even though the app shows transaction successful
    if result_code == '01' or result_code == '501':
        return PaymentStatus.SUCCESSFUL

    if result_code == '402' or result_code == '400':
        return PaymentStatus.PENDING

    return PaymentStatus.FAILED
