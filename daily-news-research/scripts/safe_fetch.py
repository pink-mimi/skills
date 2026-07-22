from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import NamedTuple
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    pass


class ValidatedUrl(NamedTuple):
    url: str
    scheme: str
    hostname: str


class FetchResult(NamedTuple):
    status: str
    payload: bytes
    final_url: str
    error: str
    content_type: str


def _resolve(hostname):
    return list({item[4][0] for item in socket.getaddrinfo(hostname,None)})


def validate_url(url,allow_http=False,resolver=_resolve):
    parsed=urlparse(str(url))
    allowed={"https"}|({"http"} if allow_http else set())
    if parsed.scheme not in allowed or not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeUrlError("仅允许受控 HTTP(S) 新闻来源")
    try:
        addresses=resolver(parsed.hostname)
    except Exception as exc:
        raise UnsafeUrlError(f"域名解析失败：{exc}") from exc
    if not addresses:
        raise UnsafeUrlError("域名没有可用地址")
    for value in addresses:
        address=ipaddress.ip_address(value)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast:
            raise UnsafeUrlError("目标地址属于本机、私网或链路本地范围")
    return ValidatedUrl(str(url),parsed.scheme,parsed.hostname.lower())


def fetch(source,opener=urllib.request.urlopen,resolver=_resolve,timeout=10):
    url=str(source.get("url") or "")
    allow_http=bool(source.get("allow_http"))
    try:
        validate_url(url,allow_http=allow_http,resolver=resolver)
        request=urllib.request.Request(url,headers={"User-Agent":"daily-news-research/2.0 (+https://github.com/pink-mimi/skills)"})
        with opener(request,timeout=timeout) as response:
            final_url=response.geturl() if hasattr(response,"geturl") else url
            validate_url(final_url,allow_http=allow_http,resolver=resolver)
            maximum=int(source.get("max_response_bytes",2097152))
            payload=response.read(maximum+1)
            if len(payload)>maximum:
                return FetchResult("blocked",b"",final_url,"响应体超过安全上限","")
            headers=getattr(response,"headers",{})
            content_type=headers.get("Content-Type","") if hasattr(headers,"get") else ""
            return FetchResult("success",payload,final_url,"",content_type)
    except UnsafeUrlError as exc:
        return FetchResult("blocked",b"",url,str(exc),"")
    except TimeoutError as exc:
        return FetchResult("timeout",b"",url,str(exc) or "请求超时","")
    except Exception as exc:
        code=getattr(exc,"code",None)
        if code==429:
            status="rate_limited"
        elif code in {401,403,451}:
            status="blocked"
        else:
            status="fetch_error"
        return FetchResult(status,b"",url,f"{type(exc).__name__}: {exc}","")
