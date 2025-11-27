--[[
  Used Lua global = pcall()

  Document about pcall :
  https://create.roblox.com/docs/reference/engine/globals/LuaGlobals#pcall
]]

local function divideByFive(n: number): number
	return n / 5
end

local success, errorMessage = pcall(divideByFive, "notANumber")  -- Results in error...

if success then
	-- Handle successful response...
else
	warn("Error message:", errorMessage)
end
