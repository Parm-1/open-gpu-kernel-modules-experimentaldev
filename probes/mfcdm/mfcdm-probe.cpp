#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WINVER
#define WINVER 0x0A00
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif
#ifndef NTDDI_VERSION
#define NTDDI_VERSION 0x0A000008
#endif

#include <windows.h>

#include <mfapi.h>
#include <mfcontentdecryptionmodule.h>
#include <mferror.h>
#include <mfidl.h>
#include <mfmediaengine.h>
#include <wrl/client.h>

#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using Microsoft::WRL::ComPtr;

constexpr int kExitSupported = 0;
constexpr int kExitUsage = 2;
constexpr int kExitInfrastructureOnly = 10;
constexpr int kExitUnsupported = 20;
constexpr int kExitApiFailure = 30;
constexpr std::size_t kMaximumInputCharacters = 2048;

struct Options {
    bool help = false;
    bool self_test = false;
    std::optional<std::wstring> key_system;
    std::optional<std::wstring> content_type;
};

struct ParseResult {
    bool ok = false;
    Options options;
    std::wstring error;
};

struct StageRecord {
    std::string name;
    bool attempted = false;
    std::string outcome;
    std::optional<HRESULT> hresult;
    std::optional<bool> supported;
};

struct Trace {
    std::optional<std::string> key_system;
    std::optional<std::string> content_type;
    std::vector<StageRecord> stages;
    std::optional<std::string> first_failure_stage;
    std::optional<std::string> first_unsupported_stage;
    std::string classification;
    int exit_code = kExitApiFailure;
};

ParseResult ParseArguments(const std::vector<std::wstring>& arguments) {
    ParseResult result;
    result.ok = true;

    for (std::size_t index = 0; index < arguments.size(); ++index) {
        const std::wstring& argument = arguments[index];
        if (argument == L"--help" || argument == L"-h") {
            result.options.help = true;
            continue;
        }
        if (argument == L"--self-test") {
            result.options.self_test = true;
            continue;
        }

        auto take_value = [&](const wchar_t* option_name,
                              std::optional<std::wstring>& destination) -> bool {
            if (destination.has_value()) {
                result.ok = false;
                result.error = std::wstring(option_name) + L" was specified more than once";
                return false;
            }
            if (index + 1 >= arguments.size()) {
                result.ok = false;
                result.error = std::wstring(option_name) + L" requires a value";
                return false;
            }
            const std::wstring& value = arguments[++index];
            if (value.empty() || value.size() > kMaximumInputCharacters) {
                result.ok = false;
                result.error = std::wstring(option_name) +
                               L" must contain 1 to 2048 characters";
                return false;
            }
            destination = value;
            return true;
        };

        if (argument == L"--key-system") {
            if (!take_value(L"--key-system", result.options.key_system)) {
                return result;
            }
            continue;
        }
        if (argument == L"--content-type") {
            if (!take_value(L"--content-type", result.options.content_type)) {
                return result;
            }
            continue;
        }

        result.ok = false;
        result.error = L"unknown argument: " + argument;
        return result;
    }

    if (result.options.content_type.has_value() &&
        !result.options.key_system.has_value()) {
        result.ok = false;
        result.error = L"--content-type requires --key-system";
        return result;
    }
    if ((result.options.help || result.options.self_test) &&
        (result.options.key_system.has_value() ||
         result.options.content_type.has_value())) {
        result.ok = false;
        result.error = L"--help and --self-test cannot be combined with probe inputs";
        return result;
    }
    if (result.options.help && result.options.self_test) {
        result.ok = false;
        result.error = L"--help and --self-test are mutually exclusive";
        return result;
    }

    return result;
}

std::string WideToUtf8(const std::wstring& value) {
    if (value.empty()) {
        return {};
    }
    if (value.size() > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
        throw std::runtime_error("wide input is too large");
    }
    const int character_count = static_cast<int>(value.size());
    const int required = WideCharToMultiByte(
        CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), character_count, nullptr, 0,
        nullptr, nullptr);
    if (required <= 0) {
        throw std::runtime_error("wide input is not valid Unicode");
    }
    std::string output(static_cast<std::size_t>(required), '\0');
    const int converted = WideCharToMultiByte(
        CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), character_count, output.data(),
        required, nullptr, nullptr);
    if (converted != required) {
        throw std::runtime_error("Unicode conversion failed");
    }
    return output;
}

std::string JsonEscape(std::string_view value) {
    static constexpr char kHex[] = "0123456789abcdef";
    std::string output;
    output.reserve(value.size() + 8U);
    for (const unsigned char byte : value) {
        switch (byte) {
            case '"': output += "\\\""; break;
            case '\\': output += "\\\\"; break;
            case '\b': output += "\\b"; break;
            case '\f': output += "\\f"; break;
            case '\n': output += "\\n"; break;
            case '\r': output += "\\r"; break;
            case '\t': output += "\\t"; break;
            default:
                if (byte < 0x20U) {
                    output += "\\u00";
                    output.push_back(kHex[(byte >> 4U) & 0x0FU]);
                    output.push_back(kHex[byte & 0x0FU]);
                } else {
                    output.push_back(static_cast<char>(byte));
                }
                break;
        }
    }
    return output;
}

std::string HResultHex(HRESULT value) {
    std::ostringstream stream;
    stream << "0x" << std::uppercase << std::hex << std::setfill('0')
           << std::setw(8)
           << static_cast<std::uint32_t>(value);
    return stream.str();
}

std::string HResultName(HRESULT value) {
    if (value == S_OK) return "S_OK";
    if (value == S_FALSE) return "S_FALSE";
    if (value == E_FAIL) return "E_FAIL";
    if (value == E_INVALIDARG) return "E_INVALIDARG";
    if (value == E_NOINTERFACE) return "E_NOINTERFACE";
    if (value == E_POINTER) return "E_POINTER";
    if (value == E_OUTOFMEMORY) return "E_OUTOFMEMORY";
    if (value == E_ACCESSDENIED) return "E_ACCESSDENIED";
    if (value == REGDB_E_CLASSNOTREG) return "REGDB_E_CLASSNOTREG";
    if (value == CLASS_E_CLASSNOTAVAILABLE) return "CLASS_E_CLASSNOTAVAILABLE";
    if (value == CO_E_NOTINITIALIZED) return "CO_E_NOTINITIALIZED";
    if (value == RPC_E_CHANGED_MODE) return "RPC_E_CHANGED_MODE";
    if (value == MF_E_PLATFORM_NOT_INITIALIZED) {
        return "MF_E_PLATFORM_NOT_INITIALIZED";
    }
    return "UNKNOWN_HRESULT";
}

void AddHResultStage(Trace& trace, std::string name, HRESULT value) {
    StageRecord stage;
    stage.name = std::move(name);
    stage.attempted = true;
    stage.outcome = SUCCEEDED(value) ? "success" : "failure";
    stage.hresult = value;
    trace.stages.push_back(std::move(stage));
}

void AddSkippedStage(Trace& trace, std::string name, std::string outcome) {
    StageRecord stage;
    stage.name = std::move(name);
    stage.attempted = false;
    stage.outcome = std::move(outcome);
    trace.stages.push_back(std::move(stage));
}

void AddSupportStage(Trace& trace, bool supported) {
    StageRecord stage;
    stage.name = "is_type_supported";
    stage.attempted = true;
    stage.outcome = supported ? "supported" : "unsupported";
    stage.supported = supported;
    trace.stages.push_back(std::move(stage));
}

void SetFirstFailure(Trace& trace, const char* stage, HRESULT value) {
    if (FAILED(value) && !trace.first_failure_stage.has_value()) {
        trace.first_failure_stage = stage;
    }
}

std::string JsonStringOrNull(const std::optional<std::string>& value) {
    if (!value.has_value()) {
        return "null";
    }
    return "\"" + JsonEscape(*value) + "\"";
}

std::string SerializeTrace(const Trace& trace) {
    std::ostringstream output;
    output << "{\n"
           << "  \"schema_version\": 1,\n"
           << "  \"probe\": \"mfcdm-probe\",\n"
           << "  \"probe_version\": 1,\n"
           << "  \"requested\": {\n"
           << "    \"key_system\": " << JsonStringOrNull(trace.key_system)
           << ",\n"
           << "    \"content_type\": " << JsonStringOrNull(trace.content_type)
           << "\n"
           << "  },\n"
           << "  \"policy\": {\n"
           << "    \"queries_explicit_key_system_only\": true,\n"
           << "    \"creates_cdm_access\": false,\n"
           << "    \"creates_cdm\": false,\n"
           << "    \"creates_session\": false,\n"
           << "    \"generates_request\": false,\n"
           << "    \"performs_network_io\": false,\n"
           << "    \"plays_media\": false\n"
           << "  },\n"
           << "  \"stages\": [\n";

    for (std::size_t index = 0; index < trace.stages.size(); ++index) {
        const StageRecord& stage = trace.stages[index];
        output << "    {\n"
               << "      \"name\": \"" << JsonEscape(stage.name) << "\",\n"
               << "      \"attempted\": "
               << (stage.attempted ? "true" : "false") << ",\n"
               << "      \"outcome\": \"" << JsonEscape(stage.outcome)
               << "\",\n";
        if (stage.hresult.has_value()) {
            output << "      \"hresult\": \""
                   << HResultHex(*stage.hresult) << "\",\n"
                   << "      \"hresult_name\": \""
                   << HResultName(*stage.hresult) << "\",\n";
        } else {
            output << "      \"hresult\": null,\n"
                   << "      \"hresult_name\": null,\n";
        }
        if (stage.supported.has_value()) {
            output << "      \"supported\": "
                   << (*stage.supported ? "true" : "false") << "\n";
        } else {
            output << "      \"supported\": null\n";
        }
        output << "    }";
        if (index + 1U != trace.stages.size()) {
            output << ',';
        }
        output << '\n';
    }

    output << "  ],\n"
           << "  \"first_failure_stage\": "
           << JsonStringOrNull(trace.first_failure_stage) << ",\n"
           << "  \"first_unsupported_stage\": "
           << JsonStringOrNull(trace.first_unsupported_stage) << ",\n"
           << "  \"classification\": \""
           << JsonEscape(trace.classification) << "\",\n"
           << "  \"exit_code\": " << trace.exit_code << ",\n"
           << "  \"claim_boundary\": "
           << "\"Public Media Foundation factory/type-support observation only; "
              "no CDM access, CDM, session, challenge, license, key, protected "
              "sample, or playback state is created.\"\n"
           << "}\n";
    return output.str();
}

void PrintUsage() {
    std::wcerr
        << L"Usage:\n"
        << L"  mfcdm-probe.exe\n"
        << L"  mfcdm-probe.exe --key-system <identifier> "
           L"[--content-type <RFC-2045 type>]\n"
        << L"  mfcdm-probe.exe --self-test\n"
        << L"  mfcdm-probe.exe --help\n\n"
        << L"With no key system, the probe stops after verifying the public Media "
           L"Foundation CDM factory interface.\n";
}

bool RunSelfTests() {
    bool passed = true;
    const auto expect = [&](bool condition, const char* name) {
        if (!condition) {
            std::cerr << "self-test failed: " << name << '\n';
            passed = false;
        }
    };

    expect(JsonEscape("a\"b\\c\n") == "a\\\"b\\\\c\\n",
           "JSON escaping");
    expect(HResultHex(E_NOINTERFACE) == "0x80004002", "HRESULT formatting");
    expect(HResultName(E_NOINTERFACE) == "E_NOINTERFACE", "HRESULT naming");
    expect(WideToUtf8(L"\u2603") == "\xE2\x98\x83", "UTF-8 conversion");

    ParseResult empty = ParseArguments({});
    expect(empty.ok && !empty.options.key_system.has_value(),
           "empty argument parsing");

    ParseResult explicit_query = ParseArguments(
        {L"--key-system", L"org.example.test", L"--content-type",
         L"video/mp4"});
    expect(explicit_query.ok &&
               explicit_query.options.key_system == L"org.example.test" &&
               explicit_query.options.content_type == L"video/mp4",
           "explicit query parsing");

    ParseResult invalid = ParseArguments({L"--content-type", L"video/mp4"});
    expect(!invalid.ok, "content type requires key system");

    Trace trace;
    trace.classification = "SELF_TEST";
    trace.exit_code = 0;
    AddHResultStage(trace, "co_initialize", S_OK);
    AddSkippedStage(trace, "cdm_factory", "not_requested");
    const std::string serialized = SerializeTrace(trace);
    expect(serialized.find("\"classification\": \"SELF_TEST\"") !=
               std::string::npos,
           "trace serialization");
    expect(serialized.find("\"creates_session\": false") != std::string::npos,
           "policy serialization");

    if (passed) {
        std::cout << "mfcdm-probe self-test passed\n";
    }
    return passed;
}

Trace RunProbe(const Options& options) {
    Trace trace;
    if (options.key_system.has_value()) {
        trace.key_system = WideToUtf8(*options.key_system);
    }
    if (options.content_type.has_value()) {
        trace.content_type = WideToUtf8(*options.content_type);
    }

    bool com_initialized = false;
    bool mf_started = false;
    bool can_continue = true;
    std::optional<bool> type_supported;

    ComPtr<IMFMediaEngineClassFactory> media_engine_factory;
    ComPtr<IMFMediaEngineClassFactory4> media_engine_factory4;
    ComPtr<IMFContentDecryptionModuleFactory> cdm_factory;

    HRESULT result = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    AddHResultStage(trace, "co_initialize", result);
    if (SUCCEEDED(result)) {
        com_initialized = true;
    } else {
        SetFirstFailure(trace, "co_initialize", result);
        can_continue = false;
    }

    if (can_continue) {
        result = MFStartup(MF_VERSION, MFSTARTUP_FULL);
        AddHResultStage(trace, "mf_startup", result);
        if (SUCCEEDED(result)) {
            mf_started = true;
        } else {
            SetFirstFailure(trace, "mf_startup", result);
            can_continue = false;
        }
    } else {
        AddSkippedStage(trace, "mf_startup", "blocked_by_prior_failure");
    }

    if (can_continue) {
        result = CoCreateInstance(
            CLSID_MFMediaEngineClassFactory, nullptr, CLSCTX_INPROC_SERVER,
            IID_PPV_ARGS(media_engine_factory.ReleaseAndGetAddressOf()));
        AddHResultStage(trace, "media_engine_class_factory", result);
        if (FAILED(result)) {
            SetFirstFailure(trace, "media_engine_class_factory", result);
            can_continue = false;
        }
    } else {
        AddSkippedStage(trace, "media_engine_class_factory",
                        "blocked_by_prior_failure");
    }

    if (can_continue) {
        result = media_engine_factory.As(&media_engine_factory4);
        AddHResultStage(trace, "media_engine_class_factory4", result);
        if (FAILED(result)) {
            SetFirstFailure(trace, "media_engine_class_factory4", result);
            can_continue = false;
        }
    } else {
        AddSkippedStage(trace, "media_engine_class_factory4",
                        "blocked_by_prior_failure");
    }

    if (!options.key_system.has_value()) {
        AddSkippedStage(trace, "cdm_factory",
                        can_continue ? "not_requested"
                                     : "blocked_by_prior_failure");
        AddSkippedStage(trace, "is_type_supported",
                        can_continue ? "not_requested"
                                     : "blocked_by_prior_failure");
    } else if (can_continue) {
        result = media_engine_factory4->CreateContentDecryptionModuleFactory(
            options.key_system->c_str(),
            IID_PPV_ARGS(cdm_factory.ReleaseAndGetAddressOf()));
        AddHResultStage(trace, "cdm_factory", result);
        if (FAILED(result)) {
            SetFirstFailure(trace, "cdm_factory", result);
            can_continue = false;
            AddSkippedStage(trace, "is_type_supported",
                            "blocked_by_prior_failure");
        } else {
            const wchar_t* content_type = options.content_type.has_value()
                                              ? options.content_type->c_str()
                                              : nullptr;
            const BOOL supported = cdm_factory->IsTypeSupported(
                options.key_system->c_str(), content_type);
            type_supported = supported != FALSE;
            AddSupportStage(trace, *type_supported);
            if (!*type_supported) {
                trace.first_unsupported_stage = "is_type_supported";
            }
        }
    } else {
        AddSkippedStage(trace, "cdm_factory", "blocked_by_prior_failure");
        AddSkippedStage(trace, "is_type_supported",
                        "blocked_by_prior_failure");
    }

    cdm_factory.Reset();
    media_engine_factory4.Reset();
    media_engine_factory.Reset();

    if (mf_started) {
        result = MFShutdown();
        AddHResultStage(trace, "mf_shutdown", result);
        if (FAILED(result)) {
            SetFirstFailure(trace, "mf_shutdown", result);
        }
    } else {
        AddSkippedStage(trace, "mf_shutdown", "not_started");
    }

    if (com_initialized) {
        CoUninitialize();
    }

    if (trace.first_failure_stage.has_value()) {
        trace.classification = "API_FAILURE";
        trace.exit_code = kExitApiFailure;
    } else if (!options.key_system.has_value()) {
        trace.classification =
            "INFRASTRUCTURE_AVAILABLE_NO_KEY_SYSTEM_REQUESTED";
        trace.exit_code = kExitInfrastructureOnly;
    } else if (type_supported.value_or(false)) {
        trace.classification = "REQUESTED_TYPE_SUPPORTED";
        trace.exit_code = kExitSupported;
    } else {
        trace.classification = "REQUESTED_TYPE_UNSUPPORTED";
        trace.exit_code = kExitUnsupported;
    }

    return trace;
}

}  // namespace

int wmain(int argc, wchar_t* argv[]) {
    std::ios::sync_with_stdio(false);

    std::vector<std::wstring> arguments;
    if (argc > 1) {
        arguments.reserve(static_cast<std::size_t>(argc - 1));
        for (int index = 1; index < argc; ++index) {
            arguments.emplace_back(argv[index]);
        }
    }

    const ParseResult parsed = ParseArguments(arguments);
    if (!parsed.ok) {
        std::wcerr << L"error: " << parsed.error << L"\n\n";
        PrintUsage();
        return kExitUsage;
    }
    if (parsed.options.help) {
        PrintUsage();
        return 0;
    }
    if (parsed.options.self_test) {
        return RunSelfTests() ? 0 : kExitApiFailure;
    }

    try {
        const Trace trace = RunProbe(parsed.options);
        std::cout << SerializeTrace(trace);
        return trace.exit_code;
    } catch (const std::exception&) {
        Trace trace;
        trace.classification = "INTERNAL_ERROR";
        trace.exit_code = kExitApiFailure;
        trace.first_failure_stage = "internal";
        AddSkippedStage(trace, "co_initialize", "internal_error");
        AddSkippedStage(trace, "mf_startup", "internal_error");
        AddSkippedStage(trace, "media_engine_class_factory", "internal_error");
        AddSkippedStage(trace, "media_engine_class_factory4", "internal_error");
        AddSkippedStage(trace, "cdm_factory", "internal_error");
        AddSkippedStage(trace, "is_type_supported", "internal_error");
        AddSkippedStage(trace, "mf_shutdown", "internal_error");
        std::cout << SerializeTrace(trace);
        return kExitApiFailure;
    }
}
