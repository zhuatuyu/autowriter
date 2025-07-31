"""
Represents the environment in which agents operate, including a shared message queue.
"""
import asyncio
from typing import Set, Dict

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.context import Context

class Environment:

    def __init__(self):
        """Initializes the environment with a message queue and a set of roles."""
        self.message_queue = asyncio.Queue()
        self.roles: dict[str, Role] = {}
        self.member_addrs: Dict[Role, Set] = {}
        self.desc = ""  # 环境描述，MetaGPT需要
        self.context = Context()  # 添加Context对象
        self.is_idle = True  # 添加is_idle属性，用于状态检查

    def add_role(self, role: Role):
        """Adds a role to the environment."""
        role.context = self.context  # 设置context
        role.set_env(self)
        self.roles[role.profile] = role

    def add_roles(self, roles: list[Role]):
        """Adds multiple roles to the environment."""
        for role in roles:
            self.add_role(role)

    async def publish(self, message: Message):
        """Publishes a message to the environment's message queue."""
        await self.message_queue.put(message)

    def publish_message(self, message: Message):
        """Synchronous method to publish a message, required by MetaGPT Role class."""
        # 将消息添加到所有角色的内存中，并设置为新消息以触发_think
        for role in self.roles.values():
            role.rc.memory.add(message)
            # 将消息设置为新消息，触发角色的_think方法
            role.rc.news = [message]

    def get_roles(self) -> dict[str, Role]:
        """Gets the roles in the environment."""
        return self.roles

    def get_role(self, name: str) -> Role | None:
        """Gets a role by name."""
        return self.roles.get(name)

    def get_addresses(self, obj):
        """Get the addresses of the object."""
        return self.member_addrs.get(obj, set())

    def set_addresses(self, obj, addresses):
        """Set the addresses of the object"""
        self.member_addrs[obj] = addresses

    async def run(self, k=1):
        """Starts the environment and all roles, running them for a specified number of rounds."""
        for _ in range(k):
            # Asynchronously run all roles
            await asyncio.gather(*[role.run() for role in self.roles.values()])