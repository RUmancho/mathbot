"""
Utility module for OpenAI API integration.
Contains custom implementations of OpenAI classes and utilities.
"""

import functools
import inspect
import time
from typing import Callable, cast, Literal, List, Union, Optional, Dict, Any
import httpx
import pydantic
from openai import OpenAI, Stream, APIResponseValidationError, AsyncOpenAI
from openai._base_client import make_request_options
from openai._models import validate_type, construct_type, BaseModel
#from pydantic import BaseModel
from openai._resource import SyncAPIResource
from openai._types import ResponseT, ModelBuilderProtocol, NotGiven, NOT_GIVEN, Headers, Query, Body
from openai._utils import maybe_transform, required_args
from openai.resources.chat import Completions as ChatCompletions
from openai.resources import Completions
from openai.types import CreateEmbeddingResponse, Completion, Embedding
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam, completion_create_params, \
    ChatCompletionToolChoiceOptionParam, ChatCompletionToolParam, ChatCompletionChunk

from langchain_openai import ChatOpenAI as GPT
from langchain_openai import OpenAIEmbeddings as OpenAIEmbeds
from langchain_core.utils import convert_to_secret_str


class ChatGPTEntry(BaseModel):
    """Model for a single chat message entry."""
    role: str
    content: str


class ResponseSchema(BaseModel):
    """Schema for API response."""
    response: ChatGPTEntry
    prompt_tokens: int
    completion_tokens: int
    available_tokens: int
    raw_openai_response: Optional[Union[ChatCompletion, Completion]] = None


def chat_completion_overload(func: Callable) -> Callable:
    """
    Decorator to handle chat completion responses.
    
    Args:
        func: The function to decorate
        
    Returns:
        Callable: The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result: Union[ChatCompletion, Stream] = func(*args, **kwargs)
        if isinstance(result, Stream):
            return result

        ndt_response = ResponseSchema(**result.model_dump(exclude_unset=True, exclude_defaults=True))
        return ndt_response.raw_openai_response

    return wrapper


class NDTChatCompletions(ChatCompletions):
    """Custom implementation of ChatCompletions for NDT API."""
    
    @required_args(["messages", "model"], ["messages", "model", "stream"])
    def create(
        self,
        *,
        messages: List[ChatCompletionMessageParam],
        model: Union[
            str,
            Literal[
                "gpt-4-1106-preview",
                "gpt-4-vision-preview",
                "gpt-4",
                "gpt-4-0314",
                "gpt-4-0613",
                "gpt-4-32k",
                "gpt-4-32k-0314",
                "gpt-4-32k-0613",
                "gpt-3.5-turbo-1106",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-0301",
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-16k-0613",
            ],
        ],
        frequency_penalty: Optional[float] = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall = NOT_GIVEN,
        functions: List[completion_create_params.Function] = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] = NOT_GIVEN,
        max_tokens: Optional[int] = NOT_GIVEN,
        n: Optional[int] = NOT_GIVEN,
        presence_penalty: Optional[float] = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat = NOT_GIVEN,
        seed: Optional[int] = NOT_GIVEN,
        stop: Union[Optional[str], List[str]] = NOT_GIVEN,
        stream: Optional[Literal[False]] = NOT_GIVEN,
        temperature: Optional[float] = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam = NOT_GIVEN,
        tools: List[ChatCompletionToolParam] = NOT_GIVEN,
        top_p: Optional[float] = NOT_GIVEN,
        user: str = NOT_GIVEN,
        extra_headers: Headers = None,
        extra_query: Query = None,
        extra_body: Body = None,
        timeout: float = NOT_GIVEN,
    ) -> ChatCompletion:
        """
        Create a chat completion.
        
        Args:
            messages: The messages to complete
            model: The model to use
            frequency_penalty: Penalty for frequency
            function_call: Function call parameters
            functions: List of functions
            logit_bias: Logit bias
            max_tokens: Maximum tokens
            n: Number of completions
            presence_penalty: Penalty for presence
            response_format: Response format
            seed: Random seed
            stop: Stop sequences
            stream: Whether to stream
            temperature: Temperature
            tool_choice: Tool choice
            tools: List of tools
            top_p: Top p
            user: User ID
            extra_headers: Extra headers
            extra_query: Extra query parameters
            extra_body: Extra body parameters
            timeout: Timeout
            
        Returns:
            ChatCompletion: The chat completion
        """
        result: ResponseSchema = self._post(
            "/chat/completions",
            body=maybe_transform(
                {
                    "messages": messages,
                    "model": model,
                    "frequency_penalty": frequency_penalty,
                    "function_call": function_call,
                    "functions": functions,
                    "logit_bias": logit_bias,
                    "max_tokens": max_tokens,
                    "n": n,
                    "presence_penalty": presence_penalty,
                    "response_format": response_format,
                    "seed": seed,
                    "stop": stop,
                    "stream": stream,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "user": user,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout
            ),
            cast_to=ResponseSchema,
            stream=stream or False,
            stream_cls=Stream[ChatCompletionChunk],
        )

        return result.raw_openai_response


class NDTCompletions(Completions):
    """Custom implementation of Completions for NDT API."""
    
    @required_args(["model", "prompt"], ["model", "prompt", "stream"])
    def create(
        self,
        *,
        model: Union[
            str,
            Literal[
                "babbage-002",
                "davinci-002",
                "gpt-3.5-turbo-instruct",
                "text-davinci-003",
                "text-davinci-002",
                "text-davinci-001",
                "code-davinci-002",
                "text-curie-001",
                "text-babbage-001",
                "text-ada-001",
            ],
        ],
        prompt: Union[str, List[str], List[int], List[List[int]], None],
        best_of: Optional[int] = NOT_GIVEN,
        echo: Optional[bool] = NOT_GIVEN,
        frequency_penalty: Optional[float] = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] = NOT_GIVEN,
        logprobs: Optional[int] = NOT_GIVEN,
        max_tokens: Optional[int] = NOT_GIVEN,
        n: Optional[int] = NOT_GIVEN,
        presence_penalty: Optional[float] = NOT_GIVEN,
        seed: Optional[int] = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] = NOT_GIVEN,
        stream: Optional[Literal[False]] = NOT_GIVEN,
        suffix: Optional[str] = NOT_GIVEN,
        temperature: Optional[float] = NOT_GIVEN,
        top_p: Optional[float] = NOT_GIVEN,
        user: str = NOT_GIVEN,
        extra_headers: Headers = None,
        extra_query: Query = None,
        extra_body: Body = None,
        timeout: float = NOT_GIVEN,
    ) -> Completion:
        """
        Create a completion.
        
        Args:
            model: The model to use
            prompt: The prompt to complete
            best_of: Best of parameter
            echo: Whether to echo the prompt
            frequency_penalty: Penalty for frequency
            logit_bias: Logit bias
            logprobs: Number of logprobs
            max_tokens: Maximum tokens
            n: Number of completions
            presence_penalty: Penalty for presence
            seed: Random seed
            stop: Stop sequences
            stream: Whether to stream
            suffix: Suffix
            temperature: Temperature
            top_p: Top p
            user: User ID
            extra_headers: Extra headers
            extra_query: Extra query parameters
            extra_body: Extra body parameters
            timeout: Timeout
            
        Returns:
            Completion: The completion
        """
        result: ResponseSchema = self._post(
            "/completions",
            body=maybe_transform(
                {
                    "model": model,
                    "prompt": prompt,
                    "best_of": best_of,
                    "echo": echo,
                    "frequency_penalty": frequency_penalty,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_tokens": max_tokens,
                    "n": n,
                    "presence_penalty": presence_penalty,
                    "seed": seed,
                    "stop": stop,
                    "stream": stream,
                    "suffix": suffix,
                    "temperature": temperature,
                    "top_p": top_p,
                    "user": user,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout
            ),
            cast_to=ResponseSchema,
            stream=stream or False,
            stream_cls=Stream[Completion],
        )
        
        time.sleep(5)  # Rate limiting
        return result.raw_openai_response


class NDTChat(SyncAPIResource):
    """Custom implementation of SyncAPIResource for NDT API."""
    
    completions: NDTChatCompletions

    def __init__(self, client: OpenAI) -> None:
        """
        Initialize NDTChat.
        
        Args:
            client: The OpenAI client
        """
        super().__init__(client)
        self.completions = NDTChatCompletions(client)


class EmbeddingResponseSchema(BaseModel):
    """Schema for embedding response."""
    data: List[Embedding]
    prompt_tokens: int
    available_tokens: int
    raw_openai_response: Optional[CreateEmbeddingResponse] = None


def embeddings_overload(func: Callable) -> Callable:
    """
    Decorator to handle embedding responses.
    
    Args:
        func: The function to decorate
        
    Returns:
        Callable: The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result: CreateEmbeddingResponse = func(*args, **kwargs)
        ndt_response = EmbeddingResponseSchema(**result.model_dump(exclude_unset=True, exclude_defaults=True))
        return ndt_response.raw_openai_response

    return wrapper


class NDTOpenAI(OpenAI):
    """Custom implementation of OpenAI for NDT API."""
    
    server_url: str = "https://api.neuraldeep.tech/"

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        """
        Initialize NDTOpenAI.
        
        Args:
            api_key: The API key
            **kwargs: Additional arguments
        """
        super().__init__(api_key=api_key, base_url=self.server_url, **kwargs)


class AsyncNDTOpenAI(AsyncOpenAI):
    """Custom implementation of AsyncOpenAI for NDT API."""
    
    server_url: str = "https://api.neuraldeep.tech/"

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        """
        Initialize AsyncNDTOpenAI.
        
        Args:
            api_key: The API key
            **kwargs: Additional arguments
        """
        super().__init__(api_key=api_key, base_url=self.server_url, **kwargs)


class ChatOpenAI(GPT):
    """Custom implementation of ChatOpenAI for NDT API."""
    
    openai_api_key: str = convert_to_secret_str('api_key')

    def __init__(self, course_api_key: str, **kwargs: Any) -> None:
        """
        Initialize ChatOpenAI.
        
        Args:
            course_api_key: The course API key
            **kwargs: Additional arguments
        """
        super().__init__(openai_api_key=course_api_key, **kwargs)


class OpenAIEmbeddings(OpenAIEmbeds):
    """Custom implementation of OpenAIEmbeddings for NDT API."""
    
    openai_api_key: str = convert_to_secret_str('api_key')

    def __init__(self, course_api_key: str, **kwargs: Any) -> None:
        """
        Initialize OpenAIEmbeddings.
        
        Args:
            course_api_key: The course API key
            **kwargs: Additional arguments
        """
        super().__init__(openai_api_key=course_api_key, **kwargs)