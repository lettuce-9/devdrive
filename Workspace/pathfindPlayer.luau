local npc = script.Parent
local human = npc.Humanoid

local PFS = game:GetService("PathfindingService")
local RUNSERVICE = game:GetService("RunService")

npc.PrimaryPart:SetNetworkOwner(nil)

local function findTarget()
	local players = game:GetService("Players"):GetPlayers()
	local nearesttarget
	local maxDistance = 5000 -- distance

	for i,player in pairs(players) do
		if player.Character then
			local target = player.Character
			local distance = (npc.HumanoidRootPart.Position - target:WaitForChild("HumanoidRootPart").Position).Magnitude

			if distance < maxDistance then
				nearesttarget = target
				maxDistance = distance
			end

		end
	end
	return nearesttarget
end

local function getPath(destination)
	local path = PFS:CreatePath()

	path:ComputeAsync(npc.HumanoidRootPart.Position, destination)

	return path
end

local function pathFindTo(destination)
	local path = getPath(destination)
	local target = findTarget()

	if target and target.Humanoid.Health > 0 then
		for i,waypoint in pairs(path:GetWaypoints()) do

			if waypoint.Action == Enum.PathWaypointAction.Jump then
				human.Jump = true
			end

			human:MoveTo(waypoint.Position)
			human.MoveToFinished:Wait()

		end
	end
end

RUNSERVICE.Heartbeat:Connect(function()
	local target = findTarget()

	if target then
		pathFindTo(target:WaitForChild("HumanoidRootPart").Position + (target:WaitForChild("HumanoidRootPart").Velocity.Unit * 7))
	end
end)
