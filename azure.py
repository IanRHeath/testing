curl -vk -H "Authorization: Bearer MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk" \
     https://ontrack-internal.amd.com/rest/api/latest/myself
* Host ontrack-internal.amd.com:443 was resolved.
* IPv6: (none)
* IPv4: 10.180.168.103
*   Trying 10.180.168.103:443...
* Connected to ontrack-internal.amd.com (10.180.168.103) port 443
* ALPN: curl offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.2 (IN), TLS handshake, Certificate (11):
* TLSv1.2 (IN), TLS handshake, Server key exchange (12):
* TLSv1.2 (IN), TLS handshake, Server finished (14):
* TLSv1.2 (OUT), TLS handshake, Client key exchange (16):
* TLSv1.2 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.2 (OUT), TLS handshake, Finished (20):
* TLSv1.2 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.2 / ECDHE-RSA-AES128-GCM-SHA256 / prime256v1 / rsaEncryption
* ALPN: server did not agree on a protocol. Uses default.
* Server certificate:
*  subject: C=US; ST=California; L=Santa Clara; O=Advanced Micro Devices, Inc.; CN=ontrack-internal.amd.com
*  start date: Apr  3 00:00:00 2025 GMT
*  expire date: May  4 23:59:59 2026 GMT
*  issuer: C=US; O=DigiCert Inc; OU=www.digicert.com; CN=GeoTrust TLS RSA CA G1
*  SSL certificate verify result: unable to get local issuer certificate (20), continuing anyway.
*   Certificate level 0: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
*   Certificate level 1: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
* using HTTP/1.x
> GET /rest/api/latest/myself HTTP/1.1
> Host: ontrack-internal.amd.com
> User-Agent: curl/8.5.0
> Accept: */*
> Authorization: Bearer MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk
>
< HTTP/1.1 200
< X-AREQUESTID: 646x50734503x18
< X-ANODEID: node3
< Referrer-Policy: strict-origin-when-cross-origin
< X-XSS-Protection: 1; mode=block
< X-Content-Type-Options: nosniff
< Strict-Transport-Security: max-age=31536000
< Set-Cookie: JSESSIONID=A7F1017204D0855F51341AD9C69EF08F; Path=/; Secure; HttpOnly
< X-Seraph-LoginReason: OK
< Set-Cookie: atlassian.xsrf.token=BMUT-0T91-7WRT-3YX2_e9832374a6fd91a21d2af020e33035b43d452283_lin; Path=/; Secure; SameSite=None
< X-RateLimit-Limit: 500
< X-RateLimit-Remaining: 499
< X-RateLimit-FillRate: 500
< X-RateLimit-Interval-Seconds: 60
< Retry-After: 0
< X-ASESSIONID: 9qavlr
< X-AUSERNAME: iheath12
< Cache-Control: no-cache, no-store, no-transform
< Content-Security-Policy: sandbox
< Content-Type: application/json;charset=UTF-8
< Transfer-Encoding: chunked
< Date: Thu, 05 Jun 2025 14:46:18 GMT
< Set-Cookie: BIGipServer~InternalApp-PT~ontrack-internal-jdcprod_rest=!tHIwBoUwIjvJf5Qdzn3MJkkc70l5F0bb4b180ITCExWzkojl/qRgihtkGVio2f2uW6Z5uAogKcHmsjo=; path=/; Httponly; Secure
<
* Connection #0 to host ontrack-internal.amd.com left intact
{"self":"https://ontrack-internal.amd.com/rest/api/2/user?username=iheath12","key":"JIRAUSER140388","name":"iheath12","emailAddress":"Ian.Heath@amd.com","avatarUrls":{"48x48":"https://ontrack-internal.amd.com/secure/useravatar?avatarId=16813","24x24":"https://ontrack-internal.amd.com/secure/useravatar?size=small&avatarId=16813","16x16":"https://ontrack-internal.amd.com/secure/useravatar?size=xsmall&avatarId=16813","32x32":"https://ontrack-internal.amd.com/secure/useravatar?size=medium&avatarId=16813"},"displayName":"Heath, Ian","active":true,"deleted":false,"timeZone":"America/Chicago","locale":"en_US","groups":{"size":6,"items":[]},"applicationRoles":{"size":1,"items":[]},"expand":"groups,applicationRoles"}
