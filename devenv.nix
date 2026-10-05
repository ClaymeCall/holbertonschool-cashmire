{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  languages.python = {
    enable = true;
    version = "3.12";
    venv.enable = true;
    venv.requirements = ''
      -r ${./backend/requirements.txt}
      -r ${./agentic/requirements.txt}
    '';
  };
}
