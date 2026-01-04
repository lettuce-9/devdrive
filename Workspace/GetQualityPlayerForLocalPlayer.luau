--[[
  Script Type = LocalScript
  ScriptLocation = StarterPlayer.StarterPlayerScripts
]]

local gS = UserSettings().GameSettings

local function settingsGraphicsListener()
	local canGetSetting, setting = pcall(function()
		local setting = gS.SavedQualityLevel.Value
		return setting
	end)
	
	if canGetSetting then
		if setting <= 2 then
			print("Low")
		elseif setting == 3 then
			print("Medium")
		elseif setting <= 9 then
			print("High")
		elseif setting == 10 then
			print("Ultra")
		end
	end
end

wait(0.5)

settingsGraphicsListener()  -- Initial check

gS:GetPropertyChangedSignal("SavedQualityLevel"):Connect(settingsGraphicsListener)  -- Only filter out property changes for SavedQualityLevel
