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
      nodejs_26
    ];
}
