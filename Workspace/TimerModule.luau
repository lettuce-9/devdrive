--[[
  Script Type = ModuleScript
  Script Parent = ReplicatedStorage (or ReplicatedStorage.ModuleScripts for cleaner structure)
]]

intermissionDuration = 180
minutes = nil
seconds = nil

local timer = {}

function timer:Format()
	minutes = math.floor(intermissionDuration / 60)
	seconds = intermissionDuration % 60
	
	return string.format("%02d:%02d", minutes, seconds)
end

function timer:StartIntermission(label)
	while intermissionDuration > 0 do
		wait(1)
		intermissionDuration = intermissionDuration - 1
		
		local formatted = self.Format()
		
		label.Text = formatted
	end
	
	if intermissionDuration == 0 then
		label.Text = "00:00"
	end
end

-- Main timer still unfinished!

return timer

--[[
	To use this module (or any module in general), use these lines :

	local RS = game:GetService("ReplicatedStorage")
	local timer = RS.TimerModule  -- or RS.ModuleScripts.TimerModule
	local label = script.Parent  -- Script should be parented in a StarterGui.ScreenGui.TextLabel

	timer:StartIntermission(label)
]]
