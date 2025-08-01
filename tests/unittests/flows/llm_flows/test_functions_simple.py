# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any
from typing import Callable

from google.adk.agents.llm_agent import Agent
from google.adk.events.event import Event
from google.adk.flows.llm_flows.functions import find_matching_function_call
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import pytest

from ... import testing_utils


def test_simple_function():
  function_call_1 = types.Part.from_function_call(
      name='increase_by_one', args={'x': 1}
  )
  function_respones_2 = types.Part.from_function_response(
      name='increase_by_one', response={'result': 2}
  )
  responses: list[types.Content] = [
      function_call_1,
      'response1',
      'response2',
      'response3',
      'response4',
  ]
  function_called = 0
  mock_model = testing_utils.MockModel.create(responses=responses)

  def increase_by_one(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x + 1

  agent = Agent(name='root_agent', model=mock_model, tools=[increase_by_one])
  runner = testing_utils.InMemoryRunner(agent)
  assert testing_utils.simplify_events(runner.run('test')) == [
      ('root_agent', function_call_1),
      ('root_agent', function_respones_2),
      ('root_agent', 'response1'),
  ]

  # Asserts the requests.
  assert testing_utils.simplify_contents(mock_model.requests[0].contents) == [
      ('user', 'test')
  ]
  assert testing_utils.simplify_contents(mock_model.requests[1].contents) == [
      ('user', 'test'),
      ('model', function_call_1),
      ('user', function_respones_2),
  ]

  # Asserts the function calls.
  assert function_called == 1


@pytest.mark.asyncio
async def test_async_function():
  function_calls = [
      types.Part.from_function_call(name='increase_by_one', args={'x': 1}),
      types.Part.from_function_call(name='multiple_by_two', args={'x': 2}),
      types.Part.from_function_call(name='multiple_by_two_sync', args={'x': 3}),
  ]
  function_responses = [
      types.Part.from_function_response(
          name='increase_by_one', response={'result': 2}
      ),
      types.Part.from_function_response(
          name='multiple_by_two', response={'result': 4}
      ),
      types.Part.from_function_response(
          name='multiple_by_two_sync', response={'result': 6}
      ),
  ]

  responses: list[types.Content] = [
      function_calls,
      'response1',
      'response2',
      'response3',
      'response4',
  ]
  function_called = 0
  mock_model = testing_utils.MockModel.create(responses=responses)

  async def increase_by_one(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x + 1

  async def multiple_by_two(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x * 2

  def multiple_by_two_sync(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x * 2

  agent = Agent(
      name='root_agent',
      model=mock_model,
      tools=[increase_by_one, multiple_by_two, multiple_by_two_sync],
  )
  runner = testing_utils.TestInMemoryRunner(agent)
  events = await runner.run_async_with_new_session('test')
  assert testing_utils.simplify_events(events) == [
      ('root_agent', function_calls),
      ('root_agent', function_responses),
      ('root_agent', 'response1'),
  ]

  # Asserts the requests.
  assert testing_utils.simplify_contents(mock_model.requests[0].contents) == [
      ('user', 'test')
  ]
  assert testing_utils.simplify_contents(mock_model.requests[1].contents) == [
      ('user', 'test'),
      ('model', function_calls),
      ('user', function_responses),
  ]

  # Asserts the function calls.
  assert function_called == 3


@pytest.mark.asyncio
async def test_function_tool():
  function_calls = [
      types.Part.from_function_call(name='increase_by_one', args={'x': 1}),
      types.Part.from_function_call(name='multiple_by_two', args={'x': 2}),
      types.Part.from_function_call(name='multiple_by_two_sync', args={'x': 3}),
  ]
  function_responses = [
      types.Part.from_function_response(
          name='increase_by_one', response={'result': 2}
      ),
      types.Part.from_function_response(
          name='multiple_by_two', response={'result': 4}
      ),
      types.Part.from_function_response(
          name='multiple_by_two_sync', response={'result': 6}
      ),
  ]

  responses: list[types.Content] = [
      function_calls,
      'response1',
      'response2',
      'response3',
      'response4',
  ]
  function_called = 0
  mock_model = testing_utils.MockModel.create(responses=responses)

  async def increase_by_one(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x + 1

  async def multiple_by_two(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x * 2

  def multiple_by_two_sync(x: int) -> int:
    nonlocal function_called
    function_called += 1
    return x * 2

  class TestTool(FunctionTool):

    def __init__(self, func: Callable[..., Any]):
      super().__init__(func=func)

  wrapped_increase_by_one = TestTool(func=increase_by_one)
  agent = Agent(
      name='root_agent',
      model=mock_model,
      tools=[wrapped_increase_by_one, multiple_by_two, multiple_by_two_sync],
  )
  runner = testing_utils.TestInMemoryRunner(agent)
  events = await runner.run_async_with_new_session('test')
  assert testing_utils.simplify_events(events) == [
      ('root_agent', function_calls),
      ('root_agent', function_responses),
      ('root_agent', 'response1'),
  ]

  # Asserts the requests.
  assert testing_utils.simplify_contents(mock_model.requests[0].contents) == [
      ('user', 'test')
  ]
  assert testing_utils.simplify_contents(mock_model.requests[1].contents) == [
      ('user', 'test'),
      ('model', function_calls),
      ('user', function_responses),
  ]

  # Asserts the function calls.
  assert function_called == 3


def test_update_state():
  mock_model = testing_utils.MockModel.create(
      responses=[
          types.Part.from_function_call(name='update_state', args={}),
          'response1',
      ]
  )

  def update_state(tool_context: ToolContext):
    tool_context.state['x'] = 1

  agent = Agent(name='root_agent', model=mock_model, tools=[update_state])
  runner = testing_utils.InMemoryRunner(agent)
  runner.run('test')
  assert runner.session.state['x'] == 1


def test_function_call_id():
  responses = [
      types.Part.from_function_call(name='increase_by_one', args={'x': 1}),
      'response1',
  ]
  mock_model = testing_utils.MockModel.create(responses=responses)

  def increase_by_one(x: int) -> int:
    return x + 1

  agent = Agent(name='root_agent', model=mock_model, tools=[increase_by_one])
  runner = testing_utils.InMemoryRunner(agent)
  events = runner.run('test')
  for request in mock_model.requests:
    for content in request.contents:
      for part in content.parts:
        if part.function_call:
          assert part.function_call.id is None
        if part.function_response:
          assert part.function_response.id is None
  assert events[0].content.parts[0].function_call.id.startswith('adk-')
  assert events[1].content.parts[0].function_response.id.startswith('adk-')


def test_find_function_call_event_no_function_response_in_last_event():
  """Test when last event has no function response."""
  events = [
      Event(
          invocation_id='inv1',
          author='user',
          content=types.Content(role='user', parts=[types.Part(text='Hello')]),
      )
  ]

  result = find_matching_function_call(events)
  assert result is None


def test_find_function_call_event_empty_session_events():
  """Test when session has no events."""
  events = []

  result = find_matching_function_call(events)
  assert result is None


def test_find_function_call_event_function_response_but_no_matching_call():
  """Test when last event has function response but no matching call found."""
  # Create a function response
  function_response = types.FunctionResponse(
      id='func_123', name='test_func', response={}
  )

  events = [
      Event(
          invocation_id='inv1',
          author='agent1',
          content=types.Content(
              role='model',
              parts=[types.Part(text='Some other response')],
          ),
      ),
      Event(
          invocation_id='inv2',
          author='user',
          content=types.Content(
              role='user',
              parts=[types.Part(function_response=function_response)],
          ),
      ),
  ]

  result = find_matching_function_call(events)
  assert result is None


def test_find_function_call_event_function_response_with_matching_call():
  """Test when last event has function response with matching function call."""
  # Create a function call
  function_call = types.FunctionCall(id='func_123', name='test_func', args={})

  # Create a function response with matching ID
  function_response = types.FunctionResponse(
      id='func_123', name='test_func', response={}
  )

  call_event = Event(
      invocation_id='inv1',
      author='agent1',
      content=types.Content(
          role='model', parts=[types.Part(function_call=function_call)]
      ),
  )

  response_event = Event(
      invocation_id='inv2',
      author='user',
      content=types.Content(
          role='user', parts=[types.Part(function_response=function_response)]
      ),
  )

  events = [call_event, response_event]

  result = find_matching_function_call(events)
  assert result == call_event


def test_find_function_call_event_multiple_function_responses():
  """Test when last event has multiple function responses."""
  # Create function calls
  function_call1 = types.FunctionCall(id='func_123', name='test_func1', args={})
  function_call2 = types.FunctionCall(id='func_456', name='test_func2', args={})

  # Create function responses
  function_response1 = types.FunctionResponse(
      id='func_123', name='test_func1', response={}
  )
  function_response2 = types.FunctionResponse(
      id='func_456', name='test_func2', response={}
  )

  call_event1 = Event(
      invocation_id='inv1',
      author='agent1',
      content=types.Content(
          role='model', parts=[types.Part(function_call=function_call1)]
      ),
  )

  call_event2 = Event(
      invocation_id='inv2',
      author='agent2',
      content=types.Content(
          role='model', parts=[types.Part(function_call=function_call2)]
      ),
  )

  response_event = Event(
      invocation_id='inv3',
      author='user',
      content=types.Content(
          role='user',
          parts=[
              types.Part(function_response=function_response1),
              types.Part(function_response=function_response2),
          ],
      ),
  )

  events = [call_event1, call_event2, response_event]

  # Should return the first matching function call event found
  result = find_matching_function_call(events)
  assert result == call_event1  # First match (func_123)


@pytest.mark.asyncio
async def test_function_call_args_not_modified():
  """Test that function_call.args is not modified when making a copy."""
  from google.adk.flows.llm_flows.functions import handle_function_calls_async
  from google.adk.flows.llm_flows.functions import handle_function_calls_live

  def simple_fn(**kwargs) -> dict:
    return {'result': 'test'}

  tool = FunctionTool(simple_fn)
  model = testing_utils.MockModel.create(responses=[])
  agent = Agent(
      name='test_agent',
      model=model,
      tools=[tool],
  )
  invocation_context = await testing_utils.create_invocation_context(
      agent=agent, user_content=''
  )

  # Create original args that we want to ensure are not modified
  original_args = {'param1': 'value1', 'param2': 42}
  function_call = types.FunctionCall(name=tool.name, args=original_args)
  content = types.Content(parts=[types.Part(function_call=function_call)])
  event = Event(
      invocation_id=invocation_context.invocation_id,
      author=agent.name,
      content=content,
  )
  tools_dict = {tool.name: tool}

  # Test handle_function_calls_async
  result_async = await handle_function_calls_async(
      invocation_context,
      event,
      tools_dict,
  )

  # Verify original args are not modified
  assert function_call.args == original_args
  assert function_call.args is not original_args  # Should be a copy

  # Test handle_function_calls_live
  result_live = await handle_function_calls_live(
      invocation_context,
      event,
      tools_dict,
  )

  # Verify original args are still not modified
  assert function_call.args == original_args
  assert function_call.args is not original_args  # Should be a copy

  # Both should return valid results
  assert result_async is not None
  assert result_live is not None


@pytest.mark.asyncio
async def test_function_call_args_none_handling():
  """Test that function_call.args=None is handled correctly."""
  from google.adk.flows.llm_flows.functions import handle_function_calls_async
  from google.adk.flows.llm_flows.functions import handle_function_calls_live

  def simple_fn(**kwargs) -> dict:
    return {'result': 'test'}

  tool = FunctionTool(simple_fn)
  model = testing_utils.MockModel.create(responses=[])
  agent = Agent(
      name='test_agent',
      model=model,
      tools=[tool],
  )
  invocation_context = await testing_utils.create_invocation_context(
      agent=agent, user_content=''
  )

  # Create function call with None args
  function_call = types.FunctionCall(name=tool.name, args=None)
  content = types.Content(parts=[types.Part(function_call=function_call)])
  event = Event(
      invocation_id=invocation_context.invocation_id,
      author=agent.name,
      content=content,
  )
  tools_dict = {tool.name: tool}

  # Test handle_function_calls_async
  result_async = await handle_function_calls_async(
      invocation_context,
      event,
      tools_dict,
  )

  # Test handle_function_calls_live
  result_live = await handle_function_calls_live(
      invocation_context,
      event,
      tools_dict,
  )

  # Both should return valid results even with None args
  assert result_async is not None
  assert result_live is not None


@pytest.mark.asyncio
async def test_function_call_args_copy_behavior():
  """Test that modifying the copied args doesn't affect the original."""
  from google.adk.flows.llm_flows.functions import handle_function_calls_async
  from google.adk.flows.llm_flows.functions import handle_function_calls_live

  def simple_fn(test_param: str, other_param: int) -> dict:
    # Modify the args to test that the copy prevents affecting the original
    return {
        'result': 'test',
        'received_args': {'test_param': test_param, 'other_param': other_param},
    }

  tool = FunctionTool(simple_fn)
  model = testing_utils.MockModel.create(responses=[])
  agent = Agent(
      name='test_agent',
      model=model,
      tools=[tool],
  )
  invocation_context = await testing_utils.create_invocation_context(
      agent=agent, user_content=''
  )

  # Create original args
  original_args = {'test_param': 'original_value', 'other_param': 123}
  function_call = types.FunctionCall(name=tool.name, args=original_args)
  content = types.Content(parts=[types.Part(function_call=function_call)])
  event = Event(
      invocation_id=invocation_context.invocation_id,
      author=agent.name,
      content=content,
  )
  tools_dict = {tool.name: tool}

  # Test handle_function_calls_async
  result_async = await handle_function_calls_async(
      invocation_context,
      event,
      tools_dict,
  )

  # Verify original args are unchanged
  assert function_call.args == original_args
  assert function_call.args['test_param'] == 'original_value'

  # Verify the tool received the args correctly
  assert result_async is not None
  response = result_async.content.parts[0].function_response.response

  # Check if the response has the expected structure
  assert 'received_args' in response
  received_args = response['received_args']
  assert 'test_param' in received_args
  assert received_args['test_param'] == 'original_value'
  assert received_args['other_param'] == 123
  assert (
      function_call.args['test_param'] == 'original_value'
  )  # Original unchanged


@pytest.mark.asyncio
async def test_function_call_args_deep_copy_behavior():
  """Test that deep copy behavior works correctly with nested structures."""
  from google.adk.flows.llm_flows.functions import handle_function_calls_async
  from google.adk.flows.llm_flows.functions import handle_function_calls_live

  def simple_fn(nested_dict: dict, list_param: list) -> dict:
    # Modify the nested structures to test deep copy
    nested_dict['inner']['value'] = 'modified'
    list_param.append('new_item')
    return {
        'result': 'test',
        'received_nested': nested_dict,
        'received_list': list_param,
    }

  tool = FunctionTool(simple_fn)
  model = testing_utils.MockModel.create(responses=[])
  agent = Agent(
      name='test_agent',
      model=model,
      tools=[tool],
  )
  invocation_context = await testing_utils.create_invocation_context(
      agent=agent, user_content=''
  )

  # Create original args with nested structures
  original_nested_dict = {'inner': {'value': 'original'}}
  original_list = ['item1', 'item2']
  original_args = {
      'nested_dict': original_nested_dict,
      'list_param': original_list,
  }

  function_call = types.FunctionCall(name=tool.name, args=original_args)
  content = types.Content(parts=[types.Part(function_call=function_call)])
  event = Event(
      invocation_id=invocation_context.invocation_id,
      author=agent.name,
      content=content,
  )
  tools_dict = {tool.name: tool}

  # Test handle_function_calls_async
  result_async = await handle_function_calls_async(
      invocation_context,
      event,
      tools_dict,
  )

  # Verify original args are completely unchanged
  assert function_call.args == original_args
  assert function_call.args['nested_dict']['inner']['value'] == 'original'
  assert function_call.args['list_param'] == ['item1', 'item2']

  # Verify the tool received the modified nested structures
  assert result_async is not None
  response = result_async.content.parts[0].function_response.response

  # Check that the tool received modified versions
  assert 'received_nested' in response
  assert 'received_list' in response
  assert response['received_nested']['inner']['value'] == 'modified'
  assert 'new_item' in response['received_list']

  # Verify original is still unchanged
  assert function_call.args['nested_dict']['inner']['value'] == 'original'
  assert function_call.args['list_param'] == ['item1', 'item2']


def test_shallow_vs_deep_copy_demonstration():
  """Demonstrate why deep copy is necessary vs shallow copy."""
  import copy

  # Original nested structure
  original = {
      'nested_dict': {'inner': {'value': 'original'}},
      'list_param': ['item1', 'item2'],
  }

  # Shallow copy (what dict() does)
  shallow_copy = dict(original)

  # Deep copy (what copy.deepcopy() does)
  deep_copy = copy.deepcopy(original)

  # Modify the shallow copy
  shallow_copy['nested_dict']['inner']['value'] = 'modified'
  shallow_copy['list_param'].append('new_item')

  # Check that shallow copy affects the original
  assert (
      original['nested_dict']['inner']['value'] == 'modified'
  )  # Original is affected!
  assert 'new_item' in original['list_param']  # Original is affected!

  # Reset original for deep copy test
  original = {
      'nested_dict': {'inner': {'value': 'original'}},
      'list_param': ['item1', 'item2'],
  }

  # Modify the deep copy
  deep_copy['nested_dict']['inner']['value'] = 'modified'
  deep_copy['list_param'].append('new_item')

  # Check that deep copy does NOT affect the original
  assert (
      original['nested_dict']['inner']['value'] == 'original'
  )  # Original unchanged
  assert 'new_item' not in original['list_param']  # Original unchanged
  assert (
      deep_copy['nested_dict']['inner']['value'] == 'modified'
  )  # Copy is modified
  assert 'new_item' in deep_copy['list_param']  # Copy is modified
