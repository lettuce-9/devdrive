--[[
    Script Type = Script
    Script Parent = ServerScriptStorage
]]

local RS = game:GetService("ReplicatedStorage")
local blacklistedCodes = require(RS.Lists.BlacklistedCodes)

local function createNewRoomCode()
	local textTable = {}
	
	for i = 1, 4 do  -- Loop table.insert 4 times to generate 4 letters in a table
    --[[
      Loop table result :

      textTable = {
        "C",
        "O",
        "D",
        "E"
      }
    ]]
    
		table.insert(textTable, string.char(math.random(65, 90)))  -- Insert a random uppercase letter
	end
	
	local result = table.concat(textTable)  -- Convert the table to a string accordingly
	
	local filtered = blacklistedCodes:Filter(result)  -- Run the stringified result through custom moderation
	
	if filtered then
		print(result)
	else
		print("- MODERATED -")
	end
end

createNewRoomCode()
