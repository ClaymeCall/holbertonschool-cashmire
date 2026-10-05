{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  packages = with pkgs;
    [
      python3
    ];
}
