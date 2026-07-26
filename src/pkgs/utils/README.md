# StormLib++ `utils` Storm Module

A Synapse Rapid Power-Up that brings useful library code into a Synapse Cortex. It is used by other Power-Ups in the StormLib++ project.

## Functions

- `getUserOrSystemOpt`
    - Pass an option string and get it from either the user vars or global vars, returns `null` if not found. Example: 
        ```
        $utils = $lib.import(slib.utils)
        $token = $utils.getUserOrSystemOpt("slib:ipinfo:token")
        ```