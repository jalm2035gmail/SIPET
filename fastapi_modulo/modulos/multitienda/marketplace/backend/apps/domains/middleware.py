from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.requests import Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi import Request as FastAPIRequest
from backend.apps.domains.models import VendorDomain
from backend.apps.vendors.models import Vendor
import re
import os

MARKETPLACE_DOMAIN = os.getenv("MARKETPLACE_DOMAIN", "marketplace.com")

class SubdomainMiddleware(BaseHTTPMiddleware):
    """Middleware para manejar subdominios y dominios personalizados"""
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        host = request.headers.get('host', '')
        subdomain = self.extract_subdomain(host)
        request.state.vendor = None
        request.state.subdomain = None
        request.state.is_custom_domain = False

        if subdomain and subdomain != 'www':
            # Buscar vendedor por subdominio
            vendor_domain = VendorDomain.query.filter_by(
                subdomain=host,
                status='active'
            ).first()
            if vendor_domain:
                request.state.vendor = vendor_domain.vendor
                request.state.subdomain = subdomain
                request.state.is_custom_domain = False
                response = await call_next(request)
                self.add_vendor_headers(response, vendor_domain.vendor)
                return response
            # Buscar por dominio personalizado
            vendor_domain = VendorDomain.query.filter_by(
                custom_domain=host,
                status='active'
            ).first()
            if vendor_domain:
                request.state.vendor = vendor_domain.vendor
                request.state.subdomain = vendor_domain.subdomain.split('.')[0]
                request.state.is_custom_domain = True
                # Forzar SSL si está configurado
                if vendor_domain.force_ssl and request.url.scheme != 'https':
                    return RedirectResponse(f"https://{host}{request.url.path}")
                response = await call_next(request)
                self.add_vendor_headers(response, vendor_domain.vendor)
                return response
            # Si no encontramos el vendedor, redirigir al dominio principal
            return RedirectResponse(f"https://{MARKETPLACE_DOMAIN}")
        # Si es el dominio principal, continuar
        response = await call_next(request)
        return response

    def extract_subdomain(self, host):
        host = host.split(':')[0]
        if host.endswith(f".{MARKETPLACE_DOMAIN}"):
            subdomain = host.replace(f".{MARKETPLACE_DOMAIN}", "")
            return subdomain
        return None

    def add_vendor_headers(self, response, vendor):
        if hasattr(response, 'headers'):
            response.headers['X-Store-ID'] = str(vendor.id)
            response.headers['X-Store-Name'] = getattr(vendor, 'store_name', '')
