import asyncio
import decimal
import json
import logging
import sys
import unittest
import unittest.mock

import aiohttp
import attr
import multidict

import base

import asyncio_stripe.stripe as stripe


class TestClient(unittest.TestCase):
    def setUp(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._session = unittest.mock.MagicMock(spec=aiohttp.ClientSession)
        self._stripe = stripe.Client(self._session, 'sekret_key')

    def tearDown(self):
        self._loop.close()

    def test_parse_charge(self):
        j = json.loads(charge_json)
        r = stripe.convert_json_response(j)
        keys = (
            'id',
            'amount',
            'amount_refunded',
            'application',
            'application_fee',
            'balance_transaction',
            'captured',
            'created',
            'currency',
            'customer',
            'description',
            'destination',
            'dispute',
            'failure_code',
            'failure_message',
            'fraud_details',
            'invoice',
            'livemode',
            'metadata',
            'on_behalf_of',
            'order',
            'outcome',
            'paid',
            'receipt_email',
            'receipt_number',
            'refunded',
            'review',
            'shipping',
            'source_transfer',
            'statement_descriptor',
            'status',
            'transfer_group',
        )
        for key in keys:
            self.assertEqual(j[key], getattr(r, key))

        self.assertEqual(r.refunds, [])

        source_keys = (
            'id',
            'address_city',
            'address_country',
            'address_line1',
            'address_line1_check',
            'address_line2',
            'address_state',
            'address_zip',
            'address_zip_check',
            'brand',
            'country',
            'customer',
            'cvc_check',
            'dynamic_last4',
            'exp_month',
            'exp_year',
            'fingerprint',
            'funding',
            'last4',
            'metadata',
            'name',
            'tokenization_method'
        )
        for key in source_keys:
            self.assertEqual(getattr(r.source, key), j['source'][key])

    def test_parse_customer(self):
        j = json.loads(customer_json)
        r = stripe.convert_json_response(j)

        keys = (
          'id',
          'account_balance',
          'created',
          'currency',
          'default_source',
          'delinquent',
          'description',
          'discount',
          'email',
          'livemode',
          'metadata',
          'shipping',
        )
        for key in keys:
            self.assertEqual(j[key], getattr(r, key))

        self.assertEqual(r.subscriptions, [])
        self.assertEqual(len(r.sources), 1)
        source_keys = (
            'id',
            'address_city',
            'address_country',
            'address_line1',
            'address_line1_check',
            'address_line2',
            'address_state',
            'address_zip',
            'address_zip_check',
            'brand',
            'country',
            'customer',
            'cvc_check',
            'dynamic_last4',
            'exp_month',
            'exp_year',
            'fingerprint',
            'funding',
            'last4',
            'metadata',
            'name',
            'tokenization_method'
        )
        for key in source_keys:
            self.assertEqual(getattr(r.sources[0], key), j['sources']['data'][0][key])

    def test_parse_card(self):
        j = json.loads(card_json)
        r = stripe.convert_json_response(j)

        keys = (
            'id',
            'address_city',
            'address_country',
            'address_line1',
            'address_line1_check',
            'address_line2',
            'address_state',
            'address_zip',
            'address_zip_check',
            'brand',
            'country',
            'customer',
            'cvc_check',
            'dynamic_last4',
            'exp_month',
            'exp_year',
            'fingerprint',
            'funding',
            'last4',
            'metadata',
            'name',
            'tokenization_method'
        )
        for key in keys:
            self.assertEqual(getattr(r, key), j[key])

    def test_error_parsing(self):
        error_body = '''
            {
                "error": {
                    "type": "invalid_request_error",
                    "message": "Customer cus_XXX does not have a linked source with ID card_YYYY.",
                    "param": "source",
                    "code": "missing"
                }
            }
        '''
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 404
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        error = json.loads(error_body)
        base.mkfuture(error, resp.json)

        with self.assertRaises(stripe.StripeError) as exc:
            base.run_until(self._stripe.create_charge(amount=103, currency='usd', k='1', j=2))
        self.assertEqual(exc.exception.type, 'invalid_request_error')
        self.assertEqual(exc.exception.charge, '')
        self.assertEqual(exc.exception.message, 'Customer cus_XXX does not have a linked source with ID card_YYYY.')
        self.assertEqual(exc.exception.code, 'missing')
        self.assertEqual(exc.exception.decline_code, '')
        self.assertEqual(exc.exception.param, 'source')
        self.assertEqual(exc.exception.http_code, 404)

    def test_param_conversion(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture(charge, resp.json)

        r = base.run_until(self._stripe.create_charge(amount=103, currency='usd', k='1', j=2,
            metadata={'md1': 'hi', 'md2': 'other'}, tf=True))
        args, kwds  = self._session.request.call_args
        self.assertEqual(kwds['params'], {
            'amount': 103,
            'currency': 'usd',
            'k': '1',
            'j': 2,
            'metadata[md1]': 'hi',
            'metadata[md2]': 'other',
            'tf': 'true'})

    def test_create_charge(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture(charge, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.create_charge(amount=103, currency='usd', k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/charges')
        self.assertEqual(kwds['params'], {'amount': 103, 'currency': 'usd', 'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(charge))

    def test_retrieve_charge(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture(charge, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.retrieve_charge('ch_aabbcc'))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/charges/ch_aabbcc')
        self.assertEqual(kwds['params'], {})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(charge))

    def test_update_charge(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture(charge, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.update_charge('ch_aabbcc', k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/charges/ch_aabbcc')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(charge))

    def test_capture_charge(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture(charge, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.capture_charge('ch_aabbcc', k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/charges/ch_aabbcc/capture')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(charge))

    def test_list_charges(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        charge = json.loads(charge_json)
        base.mkfuture({'object': 'list', 'url': '/v1/charges', 'has_more': False, 'data': [charge]}, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.list_charges(k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/charges')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, [stripe.convert_json_response(charge)])

    def test_create_customer(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        customer = json.loads(customer_json)
        base.mkfuture(customer, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.create_customer(k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(customer))

    def test_retrieve_customer(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        customer = json.loads(customer_json)
        base.mkfuture(customer, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.retrieve_customer('cus_aabbcc'))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc')
        self.assertEqual(kwds['params'], {})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(customer))

    def test_update_customer(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        customer = json.loads(customer_json)
        base.mkfuture(customer, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.update_customer('cus_aabbcc', k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(customer))

    def test_delete_customer(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        base.mkfuture({'deleted': True, 'id': 'cus_aabbcc'}, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.delete_customer('cus_aabbcc'))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'DELETE')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc')
        self.assertEqual(kwds['params'], {})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertIs(r, None)

    def test_list_customers(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        customer = json.loads(customer_json)
        base.mkfuture({'object': 'list', 'url': '/v1/customers', 'has_more': False, 'data': [customer]}, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.list_customers(k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, [stripe.convert_json_response(customer)])

    def test_create_card(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        card = json.loads(card_json)
        base.mkfuture(card, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.create_card('cus_aabbcc', 'source_token', metadata={'k': '1', 'j': 2}))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc/sources')
        self.assertEqual(kwds['params'], {'source': 'source_token', 'metadata[k]': '1', 'metadata[j]': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(card))

    def test_update_card(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        card = json.loads(card_json)
        base.mkfuture(card, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.update_card('cus_aabbcc', 'card_abc', metadata={'k': '1', 'j': 2}))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc/sources/card_abc')
        self.assertEqual(kwds['params'], {'metadata[k]': '1', 'metadata[j]': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(card))

    def test_delete_card(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        base.mkfuture({'deleted': True, 'id': 'card_aabbcc'}, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.delete_card('cus_aabbcc', 'card_aabbcc'))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'DELETE')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/customers/cus_aabbcc/sources/card_aabbcc')
        self.assertEqual(kwds['params'], {})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertIs(r, None)

    def test_create_refund(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        refund = json.loads(refund_json)
        base.mkfuture(refund, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.create_refund('ch_aabbcc', k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/refunds')
        self.assertEqual(kwds['params'], {'charge': 'ch_aabbcc', 'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(refund))

    def test_retrieve_refund(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        refund = json.loads(refund_json)
        base.mkfuture(refund, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.retrieve_refund('re_aabbcc'))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/refunds/re_aabbcc')
        self.assertEqual(kwds['params'], {})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(refund))

    def test_update_refund(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        refund = json.loads(refund_json)
        base.mkfuture(refund, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.update_refund('re_aabbcc', {'k': '1', 'j': 2}))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/refunds/re_aabbcc')
        self.assertEqual(kwds['params'], {'metadata[k]': '1', 'metadata[j]': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, stripe.convert_json_response(refund))

    def test_list_refunds(self):
        resp = unittest.mock.MagicMock(spec=aiohttp.client_reqrep.ClientResponse)
        resp.status = 200
        resp.headers = multidict.CIMultiDict({'content-type': 'application/json'})
        base.mkfuture(resp, self._session.request)
        refund = json.loads(refund_json)
        base.mkfuture({'object': 'list', 'url': '/v1/refunds', 'has_more': False, 'data': [refund]}, resp.json)

        expected_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Stripe-Version': '2017-02-14',
        }

        r = base.run_until(self._stripe.list_refunds(k='1', j=2))
        args, kwds  = self._session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.stripe.com/v1/refunds')
        self.assertEqual(kwds['params'], {'k': '1', 'j': 2})
        self.assertEqual(kwds['auth'].login, 'sekret_key')
        self.assertEqual(kwds['auth'].password, '')
        self.assertEqual(kwds['headers'], expected_headers)
        self.assertEqual(r, [stripe.convert_json_response(refund)])


# Test data scraped from API documentation
charge_json = '''
{
  "id": "ch_19t4yv2eZvKYlo2CpTQShodI",
  "object": "charge",
  "amount": 999,
  "amount_refunded": 0,
  "application": null,
  "application_fee": null,
  "balance_transaction": "txn_19XTtx2eZvKYlo2CGMbiTpim",
  "captured": true,
  "created": 1488503597,
  "currency": "usd",
  "customer": "cus_8kT8QYu4w6tXdn",
  "description": null,
  "destination": null,
  "dispute": null,
  "failure_code": null,
  "failure_message": null,
  "fraud_details": {
  },
  "invoice": "in_19t41c2eZvKYlo2Cnz4Zf1O2",
  "livemode": false,
  "metadata": {
  },
  "on_behalf_of": null,
  "order": null,
  "outcome": {
    "network_status": "approved_by_network",
    "reason": null,
    "risk_level": "normal",
    "seller_message": "Payment complete.",
    "type": "authorized"
  },
  "paid": true,
  "receipt_email": null,
  "receipt_number": null,
  "refunded": false,
  "refunds": {
    "object": "list",
    "data": [

    ],
    "has_more": false,
    "total_count": 0,
    "url": "/v1/charges/ch_19t4yv2eZvKYlo2CpTQShodI/refunds"
  },
  "review": null,
  "shipping": null,
  "source": {
    "id": "card_18SyBT2eZvKYlo2Cjcmi0i2B",
    "object": "card",
    "address_city": null,
    "address_country": null,
    "address_line1": null,
    "address_line1_check": null,
    "address_line2": null,
    "address_state": null,
    "address_zip": null,
    "address_zip_check": null,
    "brand": "Visa",
    "country": "US",
    "customer": "cus_8kT8QYu4w6tXdn",
    "cvc_check": null,
    "dynamic_last4": null,
    "exp_month": 12,
    "exp_year": 2017,
    "fingerprint": "nSkiMbFcFXyAhsMT",
    "funding": "credit",
    "last4": "4242",
    "metadata": {
    },
    "name": null,
    "tokenization_method": null
  },
  "source_transfer": null,
  "statement_descriptor": null,
  "status": "succeeded",
  "transfer_group": null
}
'''

customer_json = '''
{
  "id": "cus_ADVvZQhrsZGIRO",
  "object": "customer",
  "account_balance": 0,
  "created": 1488503267,
  "currency": "usd",
  "default_source": "card_19t4tb2eZvKYlo2CgriHQFPs",
  "delinquent": false,
  "description": null,
  "discount": null,
  "email": "cquxunih7x@virtumedix.com",
  "livemode": false,
  "metadata": {
  },
  "shipping": null,
  "sources": {
    "object": "list",
    "data": [
      {
        "id": "card_19t4tb2eZvKYlo2CgriHQFPs",
        "object": "card",
        "address_city": null,
        "address_country": null,
        "address_line1": null,
        "address_line1_check": null,
        "address_line2": null,
        "address_state": null,
        "address_zip": null,
        "address_zip_check": null,
        "brand": "Visa",
        "country": "US",
        "customer": "cus_ADVvZQhrsZGIRO",
        "cvc_check": "pass",
        "dynamic_last4": null,
        "exp_month": 3,
        "exp_year": 2018,
        "fingerprint": "nSkiMbFcFXyAhsMT",
        "funding": "credit",
        "last4": "4242",
        "metadata": {
        },
        "name": null,
        "tokenization_method": null
      }
    ],
    "has_more": false,
    "total_count": 1,
    "url": "/v1/customers/cus_ADVvZQhrsZGIRO/sources"
  }
}
'''

card_json = '''
{
  "id": "card_19t58Q2eZvKYlo2CwWmBY3yS",
  "object": "card",
  "address_city": null,
  "address_country": null,
  "address_line1": null,
  "address_line1_check": null,
  "address_line2": null,
  "address_state": null,
  "address_zip": null,
  "address_zip_check": null,
  "brand": "Visa",
  "country": "NZ",
  "customer": "cus_ADVuo4vd1LXrhI",
  "cvc_check": "pass",
  "dynamic_last4": null,
  "exp_month": 7,
  "exp_year": 2019,
  "fingerprint": "nSkiMbFcFXyAhsMT",
  "funding": "credit",
  "last4": "0008",
  "metadata": {
  },
  "name": null,
  "tokenization_method": null
}
'''

refund_json = '''
{
  "id": "re_1A7X8Y2eZvKYlo2C51ze7VD4",
  "object": "refund",
  "amount": 1293,
  "balance_transaction": "txn_1A7X8Y2eZvKYlo2CjcUTNcof",
  "charge": "ch_1A7X8P2eZvKYlo2Ctk3V2U1B",
  "created": 1491948418,
  "currency": "usd",
  "metadata": {
  },
  "reason": null,
  "receipt_number": null,
  "status": "succeeded"
}
'''


def main():
    logging.basicConfig(level=logging.DEBUG if '-v' in sys.argv else logging.CRITICAL + 1)
    unittest.main()

if __name__ == '__main__':
    main()
