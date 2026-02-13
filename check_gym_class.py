from backend.models.gym import Gym

try:
    gym = Gym(name="DevGym")
    print("Gym instance created successfully:", gym)
except Exception as e:
    print("Error while creating Gym instance:", e)

print("Gym class definition:")
print(Gym.__init__.__code__.co_varnames)
