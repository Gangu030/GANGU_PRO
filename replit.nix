# replit.nix
{ pkgs }: {
  deps = [
    pkgs.python310Full
    # Add any other system-level dependencies if needed
    # e.g., if you had specific C libraries or tools
  ];
}