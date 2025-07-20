"""
CLI Interface

Command line interface for user interaction with the common agent.
"""

import asyncio
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
import sys


class CLIInterface:
    """Command line interface for the common agent"""
    
    def __init__(self):
        self.console = Console()
        self.running = False
    
    def welcome_message(self):
        """Display welcome message"""
        welcome_text = """
# Multi-Agent System

Welcome to the intelligent multi-agent system! 

## Available Commands:
- Type your request in natural language
- Press **ESC** to interrupt current task
- Type **quit** or **exit** to stop the system
- Type **help** for more information

## Examples:
- "Create a mobile app design for a fitness tracker"
- "Analyze the market for food delivery apps"  
- "Design a user interface for an e-commerce checkout"

Ready to assist you!
        """
        
        panel = Panel(
            Markdown(welcome_text),
            title="🤖 Multi-Agent System",
            title_align="left",
            border_style="blue"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def get_user_input(self) -> Optional[str]:
        """Get user input with prompt"""
        try:
            user_input = Prompt.ask(
                "[bold cyan]You[/bold cyan]",
                default="",
                show_default=False
            )
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                return None
            
            if user_input.lower() in ['help', 'h']:
                self.show_help()
                return ""
            
            return user_input.strip()
            
        except KeyboardInterrupt:
            return None
        except EOFError:
            return None
    
    def show_help(self):
        """Show help information"""
        help_text = """
# Help Information

## How to Use:
1. **Natural Language Requests**: Just type what you want to accomplish
   - "Design a mobile app for fitness tracking"
   - "Research the competitive landscape for food delivery"
   - "Create wireframes for an e-commerce site"

2. **System Commands**:
   - `quit` or `exit` - Exit the system
   - `help` - Show this help message
   - Press `ESC` during task execution to interrupt

## Agent Capabilities:
- **User Research**: Market analysis, user surveys, competitive research
- **Product Management**: Requirements analysis, feature prioritization, roadmaps  
- **UI Design**: Wireframes, mockups, design systems, design reviews

## MCP Tools:
- **Figma Integration**: Design file management, component creation

## Tips:
- Be specific about your requirements
- The system will break down complex tasks automatically
- You can interrupt and modify requests mid-execution
        """
        
        panel = Panel(
            Markdown(help_text),
            title="📖 Help",
            border_style="green"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def display_response(self, response: str, agent_name: str = "System"):
        """Display agent response"""
        panel = Panel(
            Markdown(response),
            title=f"🤖 {agent_name}",
            title_align="left",
            border_style="green"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def display_error(self, error_message: str):
        """Display error message"""
        panel = Panel(
            f"[red]{error_message}[/red]",
            title="❌ Error",
            border_style="red"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def display_status(self, message: str):
        """Display status message"""
        self.console.print(f"[yellow]ℹ️ {message}[/yellow]")
    
    def display_working(self, message: str = "Processing your request..."):
        """Display working indicator"""
        with Live(
            Spinner("dots", text=f"[yellow]{message}[/yellow]"),
            console=self.console,
            refresh_per_second=10
        ) as live:
            return live
    
    async def run_async_with_spinner(self, coro, message: str = "Processing..."):
        """Run async coroutine with spinner"""
        with self.display_working(message):
            return await coro
    
    def display_task_progress(self, step: int, total: int, description: str):
        """Display task progress"""
        progress = f"[{step}/{total}] {description}"
        self.console.print(f"[blue]⚡ {progress}[/blue]")
    
    def display_task_interruption(self):
        """Display task interruption message"""
        self.console.print("[red]⚠️ Task interrupted by user[/red]")
        self.console.print()
    
    def goodbye_message(self):
        """Display goodbye message"""
        goodbye_text = """
# Thank You!

Thanks for using the Multi-Agent System. 

Have a great day! 🚀
        """
        
        panel = Panel(
            Markdown(goodbye_text),
            title="👋 Goodbye",
            border_style="blue"
        )
        
        self.console.print(panel) 