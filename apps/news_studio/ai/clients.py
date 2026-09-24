from openai import OpenAI
import anthropic
from ..config import CLAUDE_MODEL, OPENAI_MODELS, AI_TIMEOUT_SECONDS
from ..models.news import NewsOutput, HeadlineOutput
from .retry import retry_transient
from ..validation.news import turkish_upper
from ..prompts.news import SYSTEM_PROMPT, HEADLINE_SYSTEM_PROMPT


def _make(cls, api_key):
    try: return cls(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)
    except TypeError: return cls(api_key=api_key)


def make_openai(api_key): return _make(OpenAI, api_key)
def make_anthropic(api_key): return _make(anthropic.Anthropic, api_key)


def effort(level):
    return {"Kapalı (Tasarruflu)":"none","Düşük":"low","Orta":"medium","Yüksek":"high"}.get(level,"none")


def _usage_openai(response):
    u=getattr(response,"usage",None); inp=getattr(u,"input_tokens_details",None); out=getattr(u,"output_tokens_details",None)
    return {"input_tokens":getattr(u,"input_tokens",0),"output_tokens":getattr(u,"output_tokens",0),"cached_input_tokens":getattr(inp,"cached_tokens",0),"reasoning_tokens":getattr(out,"reasoning_tokens",0),"cache_creation_input_tokens":0,"requests":1}


def _usage_claude(response):
    u=getattr(response,"usage",None)
    return {"input_tokens":getattr(u,"input_tokens",0),"output_tokens":getattr(u,"output_tokens",0),"cached_input_tokens":getattr(u,"cache_read_input_tokens",0),"cache_creation_input_tokens":getattr(u,"cache_creation_input_tokens",0),"reasoning_tokens":0,"requests":1}


def generate_openai(client,prompt,model_name,thinking,max_tokens=2600):
    model=OPENAI_MODELS[model_name]
    def call():
        kwargs={"model":model,"instructions":SYSTEM_PROMPT,"input":prompt,"text_format":NewsOutput,"reasoning":{"effort":effort(thinking)},"max_output_tokens":max_tokens,"prompt_cache_key":"axion-haber-studio-v7"}
        try: return client.responses.parse(**kwargs)
        except TypeError:
            kwargs.pop("prompt_cache_key",None); return client.responses.parse(**kwargs)
    response=retry_transient(call)
    if response.output_parsed is None: raise ValueError("OpenAI yapılandırılmış çıktı üretmedi.")
    return response.output_parsed,{**_usage_openai(response),"provider":"OpenAI","model":model}


def generate_claude(client,prompt,thinking,max_tokens=2600):
    e=effort(thinking)
    kwargs={"model":CLAUDE_MODEL,"max_tokens":max_tokens,"messages":[{"role":"user","content":prompt}],"output_format":NewsOutput,"system":[{"type":"text","text":SYSTEM_PROMPT,"cache_control":{"type":"ephemeral"}}]}
    kwargs["thinking"]={"type":"disabled"} if e=="none" else None
    if kwargs["thinking"] is None: kwargs.pop("thinking"); kwargs["output_config"]={"effort":e}
    response=retry_transient(lambda:client.messages.parse(**kwargs))
    if response.parsed_output is None: raise ValueError("Claude yapılandırılmış çıktı üretmedi.")
    return response.parsed_output,{**_usage_claude(response),"provider":"Claude","model":CLAUDE_MODEL}


def generate(client_openai,client_claude,provider,model_name,prompt,thinking,max_tokens=2600):
    return generate_openai(client_openai,prompt,model_name,thinking,max_tokens) if provider=="OpenAI" else generate_claude(client_claude,prompt,thinking,max_tokens)


def regenerate_headlines(client_openai,client_claude,provider,model_name,content):
    prompt=f"<HABER_ICERIGI>\n{content}\n</HABER_ICERIGI>\nİki YENİ başlık üret. Yeni bilgi ekleme. baslik1 olayın nasıl/nerede yaşandığını; baslik2 sonucu veya en önemli gelişmeyi anlatsın. İkisi de tamamen büyük harf ve en fazla 9 kelime olsun."
    if provider=="OpenAI":
        model=OPENAI_MODELS[model_name]
        def call():
            kwargs={"model":model,"instructions":HEADLINE_SYSTEM_PROMPT,"input":prompt,"text_format":HeadlineOutput,"reasoning":{"effort":"none"},"max_output_tokens":450,"prompt_cache_key":"axion-haber-headline-v7"}
            try:return client_openai.responses.parse(**kwargs)
            except TypeError:
                kwargs.pop("prompt_cache_key",None);return client_openai.responses.parse(**kwargs)
        r=retry_transient(call)
        if r.output_parsed is None: raise ValueError("OpenAI başlık üretiminde çıktı alınamadı.")
        out=r.output_parsed; out.baslik1=turkish_upper(out.baslik1.strip()); out.baslik2=turkish_upper(out.baslik2.strip())
        return out,{**_usage_openai(r),"provider":"OpenAI","model":model}
    kwargs={"model":CLAUDE_MODEL,"max_tokens":500,"messages":[{"role":"user","content":prompt}],"output_format":HeadlineOutput,"thinking":{"type":"disabled"},"system":[{"type":"text","text":HEADLINE_SYSTEM_PROMPT,"cache_control":{"type":"ephemeral"}}]}
    r=retry_transient(lambda:client_claude.messages.parse(**kwargs))
    if r.parsed_output is None: raise ValueError("Claude başlık üretiminde çıktı alınamadı.")
    out=r.parsed_output; out.baslik1=turkish_upper(out.baslik1.strip()); out.baslik2=turkish_upper(out.baslik2.strip())
    return out,{**_usage_claude(r),"provider":"Claude","model":CLAUDE_MODEL}
