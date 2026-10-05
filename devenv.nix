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
      postgresql
    ];

  languages = {
    python = {
      enable = true;
      version = "3.12";
      uv.enable = true;
    };
    javascript.enable = true;
  };
}
