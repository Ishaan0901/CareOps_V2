# LangGraph agent: picks a tool (policy documents, live data or forecast) and writes the answer.
from langchain_core.messages import SystemMessage
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from tools import Search_hospital_docs
from data_tools import Get_current_status, Get_capacity_status, Get_forecast, Get_spike_status
from models import llm
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


tools=[Search_hospital_docs, Get_current_status, Get_capacity_status, Get_forecast, Get_spike_status]
llm_with_tools=llm.bind_tools(tools)



SYSTEM_PROMPT = '''You are CareOps AI, an assistant for hospital administrators at CareOps General Hospital. You help with hospital operations: beds, patient flow, waiting times, staffing, equipment, capacity levels, policies and procedures.

Rules:
    1. For any question about hospital policies, procedures, fees, thresholds or rules, ALWAYS call Search_hospital_docs first. Never answer from your own knowledge.
    2. For current or latest numbers (beds, occupancy, arrivals, waiting time, staff, alert colour) call Get_current_status. For the current capacity level or recommended actions call Get_capacity_status. For the future (arrivals, occupancy or waiting time) call Get_forecast. For unusual surges call Get_spike_status.
    3. For mixed questions (a number AND a rule, for example "Is the ED wait above the alert threshold?"), call both a data tool and Search_hospital_docs, then compare.
    4. When calling Search_hospital_docs, send a complete standalone question. Use the chat history to resolve words like "it", "its" and "and for X?" before calling.
    5. Answer ONLY using the text returned by the tools. Do not guess or invent numbers.
    6. If the tools do not contain the answer, reply exactly: "This information is not available in the hospital documents or data." Do not write a source in that case.
    7. Never give medical diagnosis, treatment or medicine advice. If asked, say you only support hospital operations and the user should consult a qualified clinician.
    8. Quote numbers, thresholds and levels exactly as returned by the tools.
    9. End the answer with the source: the document file name(s) used (Source: <file name>), and for data tools write "Source: live hospital database, data as of <data_as_of>" or "Source: ML forecast model".
    10. For greetings or small talk, reply briefly without calling a tool.
    11. If the question is not about CareOps General Hospital operations, reply: I can only help with hospital operations questions.
    12. Keep the answer clear and short. Use numbered steps only when the user asks for a procedure or actions.'''



def agent_node(state:AgentState):

    question=[SystemMessage(content=SYSTEM_PROMPT)]+state['messages']

    answer=llm_with_tools.invoke(question)

    return{'messages':[answer]}



builder=StateGraph(AgentState)

builder.add_node('agent', agent_node)
builder.add_node('tools', ToolNode(tools))

builder.add_edge(START, 'agent')
builder.add_conditional_edges('agent', tools_condition)
builder.add_edge('tools', 'agent')

graph = builder.compile()


if __name__ == "__main__":

    messages=[]

    while True:

        question=input('User: ')

        if question.lower().strip() in ['bye','exit','quit']:
            break

        result=graph.invoke({
            'messages': messages + [('user', question)]
        })

        messages=result['messages']

        print(f'\n\nAI: {messages[-1].content}\n\n')
        
