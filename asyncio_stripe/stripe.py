import aiohttp
import attr


class StripeException(Exception):
    pass


class StripeError(StripeException):
    def __init__(self, resp, body):
        self.type = None
        self.charge = None
        self.message = None
        self.code = None
        self.decline_code = None
        self.param = None

        if isinstance(body, dict):
            err = body.get('error', {})
            if err:
                self.type = err.get('type', '')
                self.charge = err.get('charge', '')
                self.message = err.get('message', '')
                self.code = err.get('code', '')
                self.decline_code = err.get('decline_code', '')
                self.param = err.get('param', '')

        def addstr(key, fmt):
            v = getattr(self, key, None)
            if v is not None and v:
                return fmt % (v,)
            return ''

        super().__init__('%s:%s%s%s%s%s%s' % (
            resp.status,
            addstr('type', ' %s:'),
            addstr('charge', ' charge: %s'),
            addstr('message', ' message: "%s"'),
            addstr('code', ' code: %s'),
            addstr('decline', ' decline: %s'),
            addstr('param', ' param: %s'),))


class ParseError(StripeException):
    pass


class DeletionError(StripeException):
    pass


@attr.s(slots=True, frozen=True)
class Charge(object):
    id = attr.ib()
    amount = attr.ib()
    amount_refunded = attr.ib()
    application = attr.ib(metadata={'expandable': True})
    application_fee = attr.ib(metadata={'expandable': True})
    balance_transaction = attr.ib(metadata={'expandable': True})
    captured = attr.ib()
    created = attr.ib()
    currency = attr.ib()
    customer = attr.ib(metadata={'expandable': True})
    description = attr.ib()
    destination = attr.ib(metadata={'expandable': True})
    dispute = attr.ib(metadata={'expandable': True})
    failure_code = attr.ib()
    failure_message = attr.ib()
    fraud_details = attr.ib()
    invoice = attr.ib(metadata={'expandable': True})
    livemode = attr.ib()
    metadata = attr.ib()
    on_behalf_of = attr.ib(metadata={'expandable': True})
    order = attr.ib(metadata={'expandable': True})
    outcome = attr.ib()
    paid = attr.ib()
    receipt_email = attr.ib()
    receipt_number = attr.ib()
    refunded = attr.ib()
    refunds = attr.ib()
    review = attr.ib(metadata={'expandable': True})
    shipping = attr.ib()
    source = attr.ib()
    source_transfer = attr.ib(metadata={'expandable': True})
    statement_descriptor = attr.ib()
    status = attr.ib()
    transfer_group = attr.ib()

    # Only when created with destination set
    transfer = attr.ib(metadata={'expandable': True}, default=None)


@attr.s(slots=True, frozen=True)
class Customer(object):
    id = attr.ib()
    account_balance = attr.ib()
    created = attr.ib()
    currency = attr.ib()
    default_source = attr.ib(metadata={'expandable': True})
    delinquent = attr.ib()
    description = attr.ib()
    discount = attr.ib()
    email = attr.ib()
    livemode = attr.ib()
    metadata = attr.ib()
    shipping = attr.ib()
    sources = attr.ib()

    # Not returned when customer has no subscriptions
    subscriptions = attr.ib(default=attr.Factory(list))

    # In documentation but not seen
    # business_vat_id = attr.ib()


@attr.s(slots=True, frozen=True)
class Card(object):
    id = attr.ib()
    address_city = attr.ib()
    address_country = attr.ib()
    address_line1 = attr.ib()
    address_line1_check = attr.ib()
    address_line2 = attr.ib()
    address_state = attr.ib()
    address_zip = attr.ib()
    address_zip_check = attr.ib()
    brand = attr.ib()
    country = attr.ib()
    customer = attr.ib(metadata={'expandable': True})
    cvc_check = attr.ib()
    dynamic_last4 = attr.ib()
    exp_month = attr.ib()
    exp_year = attr.ib()
    fingerprint = attr.ib()
    funding = attr.ib()
    last4 = attr.ib()
    metadata = attr.ib()
    name = attr.ib()
    tokenization_method = attr.ib()

    # Managed accounts only
    # account = attr.ib(metadata={'expandable': True})
    # currency = attr.ib(metadata={'expandable': True})
    # default_for_currency = attr.ib(metadata={'expandable': True})
    # recipient = attr.ib(metadata={'expandable': True})

    # In documentation but not seen
    # available_payout_methods = attr.ib()
    # three_d_secure = attr.ib()


@attr.s(slots=True, frozen=True)
class Refund(object):
    id = attr.ib()
    amount = attr.ib()
    balance_transaction = attr.ib(metadata={'expandable': True})
    charge = attr.ib(metadata={'expandable': True})
    created = attr.ib()
    currency = attr.ib()
    metadata = attr.ib()
    reason = attr.ib()
    receipt_number = attr.ib()
    status = attr.ib()

    # In documentation but not seen
    # description = attr.ib()


class Client(object):
    def __init__(self, session, pk):
        '''
        Create a new Stripe client

        @param session  - aiohttp session
        @param pk       - private stripe key
        '''
        self._session = session
        self._auth = aiohttp.BasicAuth(pk)
        self._url = 'https://api.stripe.com/v1'

    async def _req(self, method, page, params=None):
        '''
        Issue a request to the given page relative to the base Stripe API URL.

        @param method   - http method
        @param page     - page relative to base stripe API URL
        @param params   - data to post, if any
        @return         - Stripe Object

        @raises StripeError on error from stripe
        @raises ParseError on failing to parse Stripe Object
        '''
        url = self._url + '/' + page.lstrip('/')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        if params is None:
            params = {}

        # Turn any dictionaries into parameters
        for key in [k for k, v in params.items() if isinstance(v, dict)]:
            for subkey, v in params[key].items():
                params['%s[%s]' % (key, subkey)] = v
            del params[key]

        # Booleans to strings
        params.update({
            k: str(v).lower()
            for k, v in params.items()
            if isinstance(v, bool)})

        r = await self._session.request(
                method.upper(),
                url,
                params=params,
                auth=self._auth,
                headers=headers)

        if r.headers.get('Content-Type', '').startswith('application/json'):
            body = await r.json()
        else:
            body = await r.read()

        if r.status != 200:
            raise StripeError(r, body)

        if method.upper() == 'DELETE':
            if not body.get('deleted', False):
                raise DeletionError('Failed to delete %s' % (body.get('id'),))
            return

        if 'object' not in body:
            raise ParseError('Stripe response missing "object": %s' % (body,))

        return convert_json_response(body)

    async def create_charge(self, amount, currency, **kwds):
        '''
        Create a new charge.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#create_charge

        @param amount   - amount to be charged, in cents
        @param currency - charge currency
        @return - created Charge instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        params = {'amount': amount, 'currency': currency, **kwds}
        return await self._req('post', '/charges', params=params)

    async def retrieve_charge(self, charge_id):
        '''
        Retrieve a charge

        @param charge_id - charge identifier
        @return - matching Charge instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req('get', '/charges/%s' % (charge_id,))

    async def update_charge(self, charge_id, **kwds):
        '''
        Update a charge.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#update_charge

        @param charge_id - charge identifier
        @return - updated Charge instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req(
                'post',
                '/charges/%s' % (charge_id,),
                params=kwds)

    async def capture_charge(self, charge_id, **kwds):
        '''
        Capture payment of a charge previously created with capture=False.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#capture_charge

        @param charge_id - charge identifier
        @return - captured Charge instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req(
                'post',
                '/charges/%s/capture' % (charge_id,),
                params=kwds)

    async def list_charges(self, **kwds):
        '''
        Return a list of previously created charges matching the given
        parameters.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#list_charges

        @return - list of matching Charge instances

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req('get', '/charges', params=kwds)

    async def create_customer(self, **kwds):
        '''
        Create a new customer

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#create_customer

        @return - created Customer

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req('post', '/customers', params=kwds)

    async def retrieve_customer(self, customer_id):
        '''
        Retrieve a customer

        @param customer_id  - customer identifier
        @return - matching Customer instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req('get', '/customers/%s' % (customer_id,))

    async def update_customer(self, customer_id, **kwds):
        '''
        Update a customer

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#update_customer

        @param customer_id  - customer identifier
        @return - updated Customer

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req(
            'post',
            '/customers/%s' % (customer_id,),
            params=kwds)

    async def delete_customer(self, customer_id):
        '''
        Delete a customer

        @param customer_id  - customer identifier

        @raises StripeError - Parsed errors from stripe
        '''
        await self._req('delete', '/customers/%s' % (customer_id,))

    async def list_customers(self, **kwds):
        '''
        Return a list of previously created charges matching the given
        parameters.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#list_charges

        @return - list of matching Charge instances

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Charge instance failed
        '''
        return await self._req('get', '/customers', params=kwds)

    async def create_card(self, customer_id, source, metadata=None):
        '''
        Create a new credit card for the specified customer

        @param customer_id  - customer identifier
        @param source       - token or dictionary with credit card details
        @param metadata     - map of metadata if any
        @return             - new card

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Card instance failed
        '''
        params = {'source': source}
        if metadata is not None:
            params['metadata'] = metadata

        return await self._req(
                'post',
                '/customers/%s/sources' % (customer_id,),
                params=params)

    async def delete_card(self, customer_id, source_id):
        '''
        Delete a credit card from the specified customer

        @param customer_id  - customer identifier
        @param source_id    - id of card to be deleted

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Card instance failed
        '''
        await self._req(
            'delete',
            '/customers/%s/sources/%s' % (customer_id, source_id))

    async def create_refund(self, charge_id, **kwds):
        '''
        Refund all or part of a charge.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#create_refund

        @param charge_id - charge identifier
        @return - Refund instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Refund instance failed
        '''
        params = {'charge': charge_id}
        params.update(kwds)
        return await self._req('post', '/refunds', params)

    async def retrieve_refund(self, refund_id):
        '''
        Retrieve a refund

        @param refund_id    - refund identifier
        @return - matching Refund instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Refund instance failed
        '''
        return await self._req('get', '/refunds/%s' % (refund_id,))

    async def update_refund(self, refund_id, metadata):
        '''
        Update the metadata on a refund.  Keys can be removed by setting the
        value to None for that key.

        @param refund_id    - refund identifier
        @param metadata     - MultiDict of metadata
        @return - updated Refund instance

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Refund instance failed
        '''
        params = {'metadata': metadata}
        return await self._req('post', '/refunds/%s' % (refund_id,), params)

    async def list_refunds(self, **kwds):
        '''
        Return a list of previously refunds matching the given parameters.

        Keyword arguments can be passed as defined by:
        https://stripe.com/docs/api/curl#list_refunds

        @return - list of matching Refund instances

        @raises StripeError - Parsed errors from stripe
        @raises ParseError  - Parsing Refund instance failed
        '''
        return await self._req('get', '/refunds', params=kwds)


cls_map = {
    'charge': Charge,
    'customer': Customer,
    'card': Card,
    'refund': Refund,
}


def convert_json_response(resp):
    if isinstance(resp, list):
        return [convert_json_response(r) for r in resp]
    elif isinstance(resp, dict) and resp.get('object', '') in cls_map:
        resp = resp.copy()
        cls = cls_map[resp['object']]
        del resp['object']

        for k in (k for k, v in resp.items() if isinstance(v, (list, dict))):
            resp[k] = convert_json_response(resp[k])

        return cls(**resp)
    elif isinstance(resp, dict) and resp.get('object', '') == 'list':
        return [convert_json_response(r) for r in resp['data']]

    return resp


def create_json_request(req):
    if isinstance(req, tuple(cls_map.values())):
        return create_json_request(attr.asdict(req))
    elif isinstance(req, dict):
        return {k: create_json_request(v) for k, v in req.items()}
    elif isinstance(req, list):
        return [create_json_request(v) for v in req]
    return req
