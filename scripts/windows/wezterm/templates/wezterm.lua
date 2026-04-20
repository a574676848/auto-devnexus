local wezterm = require 'wezterm'
local config = wezterm.config_builder()

local user_profile = os.getenv('USERPROFILE')
local cleanup_script = user_profile .. '/.wezterm_cleanup.ps1'
local image_handler_script = user_profile .. '/.wezterm_img_handler.ps1'
local pwsh_path = 'C:/Program Files/PowerShell/7/pwsh.exe'

if wezterm.target_triple == 'x86_64-pc-windows-msvc' then
  local cleanup_ok = pcall(wezterm.background_child_process, {
    'powershell.exe',
    '-NoProfile',
    '-WindowStyle',
    'Hidden',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    cleanup_script,
  })

  if not cleanup_ok then
    wezterm.log_warn('启动清理脚本失败，将继续加载 WezTerm 配置。')
  end
end

config.default_prog = { pwsh_path, '-NoLogo' }
config.default_cwd = wezterm.home_dir
config.color_scheme = 'AdventureTime'
config.font_size = 13.0
config.window_padding = {
  left = 10,
  right = 10,
  top = 8,
  bottom = 8,
}

local function smart_paste(window, pane)
  local success, stdout = wezterm.run_child_process({
    'powershell.exe',
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    image_handler_script,
  })

  if success and stdout then
    local img_path = stdout:gsub('[\r\n]+$', '')
    if img_path ~= '' then
      pane:send_paste(img_path)
      return
    end
  end

  window:perform_action(wezterm.action.PasteFrom 'Clipboard', pane)
end

local function copy_or_interrupt(window, pane)
  local has_selection = window:get_selection_text_for_pane(pane) ~= ''
  if has_selection then
    window:perform_action(wezterm.action.CopyTo 'Clipboard', pane)
    window:perform_action(wezterm.action.ClearSelection, pane)
    return
  end

  window:perform_action(
    wezterm.action.SendKey { key = 'c', mods = 'CTRL' },
    pane
  )
end

config.keys = {
  {
    key = 'V',
    mods = 'CTRL',
    action = wezterm.action_callback(smart_paste),
  },
  {
    key = 'v',
    mods = 'CTRL',
    action = wezterm.action_callback(smart_paste),
  },
  {
    key = 'c',
    mods = 'CTRL',
    action = wezterm.action_callback(copy_or_interrupt),
  },
}

return config
