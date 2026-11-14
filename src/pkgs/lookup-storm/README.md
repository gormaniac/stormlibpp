# lookup-storm

Lookup common atomic indicators in Synapse as strings rather than a `<form>=<valu>` pair.

Not every Synapse user can, or should be expected to, know the necessary form names for common atomic indicators that analysts use. They need a way to query for these values quickly and without the form. Besides, sometimes it's just faster to type `lookup something` than `[form:type?=something]`.

Adds a `lookup` command to a Synapse instance that accepts multiple input strings and yields Synapse nodes that have the input items as primary values. The nodes are created if they don't already exist. The input items are used to attempt to lift nodes of the following forms, in this order, using `?=`:
```
hash:md5
hash:sha1
hash:sha256
inet:cidr4
inet:ipv4
inet:ipv6
inet:fqdn
inet:email
inet:server
inet:url
file:path
```

## Examples

### Lookup a single IP address by string
```
lookup 1.1.1.1
```

### Lookup a hash, an IP address, and a file path in one command
```
lookup "d41d8cd98f00b204e9800998ecf8427e" "1.1.1.1" "C:\Windows\System32\calc.exe"
```

### Lookup a url and a tcp server
```
lookup http://example.com tcp://1.1.1.1:80
```
