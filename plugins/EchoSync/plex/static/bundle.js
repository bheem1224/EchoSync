var e = 1024, t = 2048, n = 4096, r = 8192, i = 32768, a = 1 << 25, o = 65536, s = 1 << 19, c = 1 << 20, l = 1 << 25, u = 1 << 21, d = 1 << 22, f = 1 << 23, p = 1 << 27, m = 1 << 26, h = Symbol("$state"), g = Symbol("component"), _ = Symbol("legacy props"), ee = Symbol(""), te = Symbol("attributes"), ne = Symbol("class"), re = Symbol("style"), ie = Symbol("text"), ae = Symbol("form reset"), oe = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), se = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), v = {}, y = Symbol("uninitialized");
function ce() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function le(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function ue() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var b = !1;
function de(e) {
	b = e;
}
var x;
function S(e) {
	if (e === null) throw le(), v;
	return x = e;
}
function fe() {
	return S(/* @__PURE__ */ Pr(x));
}
function C(e) {
	if (b) {
		if (/* @__PURE__ */ Pr(x) !== null) throw le(), v;
		x = e;
	}
}
function pe(e = 1) {
	if (b) {
		for (var t = e, n = x; t--;) n = /* @__PURE__ */ Pr(n);
		x = n;
	}
}
function me(e = !0) {
	for (var t = 0, n = x;;) {
		if (Hr(n) === 8) {
			var r = $r(n) ?? "";
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Pr(n);
		e && Yr(n), n = i;
	}
}
function he(e) {
	if (!e || Hr(e) !== 8) throw le(), v;
	return $r(e) ?? "";
}
// node_modules/svelte/src/internal/shared/utils.js
var ge = Array.isArray, _e = Array.prototype.indexOf, ve = Array.prototype.includes, ye = Array.from, be = Object.keys, xe = Object.defineProperty, Se = Object.getOwnPropertyDescriptor, Ce = Object.getOwnPropertyDescriptors, we = Object.prototype, Te = Array.prototype, Ee = Object.getPrototypeOf, De = Object.isExtensible, Oe = () => {};
function ke(e) {
	return e();
}
function Ae(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function je() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function Me(e) {
	var t = U;
	if (t === null) return e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ne(e, t);
}
function Ne(e, t) {
	if (e === v) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
function Pe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
function Fe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ie() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Le(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Re() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ze() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Be(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function He() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ue() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function We() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var Ge = !1;
function Ke() {
	Ge = !0;
}
// node_modules/svelte/src/internal/client/context.js
var w = null;
function qe(e) {
	w = e;
}
function Je(e, t = !1, n) {
	w = {
		p: w,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: U,
		l: Ge && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ye(e) {
	var t = w, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) ln(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, w = t.p, Xe(e);
}
function Xe(e = {}) {
	return xe(e, g, { value: !0 }), e;
}
function Ze() {
	return !Ge || w !== null && w.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Qe = [];
function $e() {
	var e = Qe;
	Qe = [], Ae(e);
}
function T(e) {
	if (Qe.length === 0 && !Rt) {
		var t = Qe;
		queueMicrotask(() => {
			t === Qe && $e();
		});
	}
	Qe.push(e);
}
function et() {
	for (; Qe.length > 0;) $e();
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function tt(e) {
	return e === this.v;
}
function nt(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function rt(e) {
	return !nt(e, this.v);
}
// node_modules/svelte/src/internal/client/custom-renderer/state.js
var it = null;
// node_modules/svelte/src/internal/client/reactivity/async.js
function at(e, t, n, r) {
	var i = U, a = t.map(Ze() ? ft : gt), s = e.filter((e) => !e.settled);
	if (s.length > 0) {
		var c = ot(), l = lt();
		(s.length === 1 ? s[0].promise : Promise.all(s.map((e) => e.promise))).then(() => {
			if (!(i.f & 16384)) {
				c(s[0].run.get_batch());
				try {
					u();
				} catch (e) {
					Ne(e, i);
				}
				st();
			}
		}).finally(l);
	} else u();
	function u() {
		if (!e.some((e) => e.failed)) {
			if (n.length === 0) r(a);
			else {
				var t = n.map((e) => /* @__PURE__ */ mt(e)), s = null;
				_n(() => {
					for (var e of t) if (ht(e)) {
						Y(e);
						return;
					}
					s === null ? s = L(() => {
						try {
							r([...a, ...t]);
						} catch (e) {
							Ne(e, i);
						}
					}) : j.revalidate_branch(s);
				}, o);
			}
		}
	}
}
function ot() {
	var e = U, t = B, n = w, r = j;
	return function(i = r) {
		In(e), H(t), qe(n), i !== null && !(e.f & 16384) && E(i).activate();
	};
}
function st(e = !0) {
	In(null), H(null), qe(null), e && j?.deactivate();
}
var ct = null;
function lt() {
	for (var e = U, t = e.b, n = E(j), r = t; r && !r.is_pending;) r = r.parent;
	return n.increment(e), r?.increment(e, n), t?.update_effect_pending(1), () => {
		E(n).decrement(e), r?.decrement(e, n), t?.update_effect_pending(-1);
	};
}
function E(e) {
	for (; e.merged !== null;) e = e.merged;
	return e;
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var ut = ~(t | n | e);
function D(e, t) {
	e.f = e.f & ut | t;
}
function dt(t) {
	t.f & 512 || t.edges === null ? D(t, e) : D(t, n);
}
/*#__NO_SIDE_EFFECTS__*/
function ft(e) {
	var n = 2 | t;
	return U !== null && (U.f |= s), {
		ctx: w,
		deps: null,
		dv: null,
		edges: null,
		effects: null,
		equals: tt,
		f: n,
		fn: e,
		reactions: null,
		rv: 0,
		v: y,
		wv: 0,
		parent: U,
		ac: null
	};
}
var pt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function mt(e, t, n, r) {
	var i = Tt(y);
	i.f |= d;
	var a = /* @__PURE__ */ new Set(), o = ct, s = o && j, c = o && [];
	function l(e = !1) {
		var t = c;
		c = e ? null : [], e && (s = null);
		for (let e of t) e();
	}
	return mn(() => {
		var t = U, n = je();
		try {
			var u = e();
			if (u === y) return;
			var d = Promise.resolve(u), f = J?.signal;
			d.then((e) => {
				f?.aborted || n.resolve(e);
			}, (e) => {
				f?.aborted || e === oe && o === null || n.reject(e === oe ? pt : e);
			}).finally(st);
		} catch (e) {
			n.reject(e);
		}
		var p = j, m = lt();
		p.async_deriveds.get(t)?.reject(pt), a.add(n), p.async_deriveds.set(t, n);
		let h = (e, u = void 0) => {
			if (c !== null && u !== pt && (s ??= p, E(p) !== E(s))) c.push(() => {
				var r = !!(t.f & 16384) || (p.linked ? p.async_deriveds.get(t) !== n : !E(p).linked);
				h(e, r ? pt : u);
			});
			else {
				if (m(), a.delete(n), u) {
					if (c !== null && s !== null && (a.size > 0 || u === pt) && E(s) === E(p) && E(p).async_deriveds.get(t) === n) {
						s = null, l();
						return;
					}
					if (u === pt) return;
				}
				var d = i.equals(e) && !u && !(i.f & 8388608);
				E(p).capture(i, u ?? e, d, !!u), o !== null && (o.switch(p), o.continued.push(() => l(!0)), o = null), r?.(u), r = void 0;
			}
		};
		n.promise.then(h, (e) => h(null, e || "unknown"));
	}), sn(() => {
		for (let e of a) e.reject(pt);
	}), i;
}
function ht(e) {
	return (N?.get(e) ?? e).v === y;
}
/*#__NO_SIDE_EFFECTS__*/
function gt(e) {
	let t = /* @__PURE__ */ ft(e);
	return t.equals = rt, t;
}
function _t(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) R(t[n]);
	}
}
function vt(e) {
	var t = U, n = e.parent;
	if (!z && n !== null && e.v !== y && n.f & 24576) return ce(), dt(e), e.v;
	In(n);
	try {
		return _t(e), ir(e);
	} finally {
		In(t);
	}
}
function yt(e) {
	var t = e;
	if (Jn(t)) {
		var n = F?.records, r = n?.get(t);
		r !== void 0 && Gn(r.deps, r.dv) ? (n.delete(t), dr(t, r)) : vt(t);
	}
}
function bt(e) {
	var t = P, n = t.get(e);
	if (n !== void 0) return n;
	var r = F, i = N.get(e), a = i ?? e, o = i === void 0 ? (e.f & m) !== 0 : i.assigned, s = r.get_record(e);
	return o && !Kn((s ?? e).deps, a.wv) ? n = a : s !== void 0 && Gn(s.deps, s.dv) ? n = s : i === void 0 && !o && e.dv !== null && Gn(e.deps, e.dv) ? n = e : (vt(e), n = r.records?.get(e) ?? e), e.f & 512 && t.set(e, n), n;
}
function xt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.f & 134217728) && (t.teardown?.(), nr(t), t.fn !== null && (t.teardown = Oe), gr(t), yn(t));
}
function St(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && _r(t);
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var Ct = /* @__PURE__ */ new Set(), wt = !1;
function Tt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: tt,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Et(e, t) {
	let n = Tt(e, t);
	return Ln(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function O(e, t = !1, n = !0) {
	let r = Tt(e);
	return t || (r.equals = rt), Ge && n && w !== null && w.l !== null && (w.l.s ??= []).push(r), r;
}
function k(e, t, n = !1) {
	return B !== null && (!V || B.f & 131072) && Ze() && B.f & 4325394 && (W === null || !W.has(e)) && Ue(), Dt(e, n ? Er(t) : t, Bt);
}
function Dt(e, t, n = null) {
	var r = e.equals(t) && !(e.f & 8388608), i = N?.get(e);
	if (!r || i !== void 0 && (i.e || !e.equals.call(i, t))) {
		var a = Kt.ensure();
		(e.f & 67110914) == 2050 && vt(e), a.capture(e, t, r, !1, n), Ze() && U !== null && U.f & 1024 && !(U.f & 96) && (q === null ? Rn([e]) : q.push(e));
	} else z && Ft(e);
	return t;
}
function Ot() {
	wt = !1, tn(kt);
}
function kt() {
	for (let e of Ct) {
		e.f & 1024 && D(e, n);
		let t;
		try {
			t = Jn(e);
		} catch {
			t = !0;
		}
		t && _r(e);
	}
	Ct.clear();
}
function At(e) {
	k(e, e.v + 1);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var A = null, jt = null, j = null, Mt = null, M = null;
function Nt(e) {
	M = e;
}
function Pt(e) {
	var t = M = {
		reverted_values: new Map(M?.reverted_values),
		derived_cache: /* @__PURE__ */ new Map(),
		parent: M
	};
	for (let [n, r] of e ?? []) t.reverted_values.set(n, r);
	return t;
}
function Ft(e) {
	for (var t = M; t !== null; t = t.parent) t.reverted_values.delete(e), t.derived_cache.clear();
}
var N = null, P = null, F = null, It = null, Lt = /* @__PURE__ */ new Set(), Rt = !1, zt = null, Bt = null, Vt = 0, Ht = null, Ut = 0, Wt = 1, Gt = null, Kt = class r {
	id = Wt++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	records = null;
	folded = [];
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = null;
	#i = /* @__PURE__ */ new Map();
	#a = [];
	#o = /* @__PURE__ */ new Set();
	#s = /* @__PURE__ */ new Set();
	is_fork = !1;
	merged = null;
	merge_requests = /* @__PURE__ */ new Set();
	#c = !1;
	constructor() {
		jt === null ? A = jt = this : (jt.next = this, this.prev = jt), jt = this;
	}
	#l() {
		if (this.is_fork) return !0;
		for (let e of this.#n.keys()) if (this.is_blocked_by(e)) return !0;
		return !1;
	}
	#u(e) {
		return this.#o.has(e) || !!(e.f & 33554432) && !this.#s.has(e);
	}
	is_skipped(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#u(t)) return !0;
		return !1;
	}
	is_blocked_by(e, t = null) {
		for (var n = e; n !== null && n !== t; n = n.parent) if (this.#u(n) || (n.f & 16512) == 128 && n.b.is_pending) return !1;
		return !0;
	}
	skip_effect(e) {
		this.#o.add(e), this.#s.delete(e);
	}
	unskip_effect(e) {
		(this.#o.delete(e) || !this.#s.has(e) && (e.f & 33554432 || this.folded.some((t) => t.#o.has(e)))) && this.revalidate_branch(e), this.#s.add(e);
	}
	unskip_new_effect(e) {
		this.#s.add(e);
	}
	revalidate_branch(e) {
		for (var t = e.first; t !== null; t = t.next) {
			var r = t.f;
			!(r & 24576) && !this.#u(t) && (!(r & 131168) && t.fn !== null && this.schedule(t, n), this.revalidate_branch(t));
		}
	}
	#d() {
		var t = [];
		for (let a of this.#a) if (!(a.f & 16384 || !(a.f & 6144))) {
			for (var n = a, r = !1; n.parent !== null;) {
				n = n.parent;
				var i = n.f;
				if (i & 96) {
					if (!(i & 1024)) {
						r = !0;
						break;
					}
					n.f ^= e;
				}
			}
			r || t.push(n);
		}
		return this.#a = [], t;
	}
	#f() {
		if (j = Mt = this, M?.derived_cache.clear(), this.started = !0, Gt = this.id, this.#i.size > 0) {
			for (let [e, t] of this.#i) this.#S(e, t);
			this.#i.clear();
		}
		this.activate();
		for (var e = zt = [], t = [], i = [], a = Bt = []; this.#a.length > 0;) {
			Vt++ > 1e3 && (this.#T(), Jt());
			for (let n of this.#d()) try {
				this.#m(n, e, t, i);
			} catch (e) {
				throw nn(n, !0), this.#l() || this.discard(), e;
			}
			if (this.#a.length > 0) {
				for (let e of t) this.#a.push(e);
				for (let t of e) this.#a.push(t);
				t.length = 0, e.length = 0;
			}
		}
		if (j = null, a.length > 0) {
			var o = r.ensure();
			for (let e of a) e.f & 1024 || o.schedule(e, n);
		}
		if (zt = null, Bt = null, this.merge_requests.size > 0) {
			let n = Array.from(this.merge_requests, E).filter((e) => e !== this && e.linked && !e.is_fork).sort((e, t) => e.id - t.id);
			if (this.merge_requests.clear(), n.length > 0) {
				this.#y(t), this.#y(e);
				for (var s = this, c = n.length; c--;) {
					var l = n[c];
					l !== s && (l.#_(s), s = l);
				}
				s.#f();
				return;
			}
		}
		if (this.#l()) {
			this.#y(t), this.#y(e);
			for (let e of this.#o) nn(e);
			a.length > 0 && j.#f();
			return;
		}
		let u = this.#h();
		if (u) this.#y(t), this.#y(e), u.#_(this), u.#f();
		else {
			for (let t of i) t.is_pending && t.is_ready(this) && t.reveal(e);
			this.#C(!0), this.#x(this.#e), Qt(e, Qt(t)), this.#r?.resolve();
			var d = j;
			if (this.#n.size === 0 && (this.#a.length === 0 || d !== null) && this.#T(), d !== null) {
				if (M !== null) for (let [e, t] of M.reverted_values) d.previous.get(e)?.wv !== t.wv && M.reverted_values.delete(e);
				d.#f();
			}
		}
	}
	#p(e) {
		var t = new Set(e), r = /* @__PURE__ */ new Set();
		for (let e of t) {
			var i = e.reactions;
			if (i !== null) for (let e of i) {
				var a = e.f;
				if (a & 2) a & 1024 && D(e, n), t.add(e);
				else {
					var o = e;
					r.has(o) || (r.add(o), !(a & 155648) && !this.is_skipped(o) && this.schedule(o, n));
				}
			}
		}
	}
	#m(t, n, r, i) {
		t.f ^= e;
		for (var a = t.first; a !== null;) {
			var o = a.f, s = !!(o & 96);
			if (!(s && o & 1024 || o & 139264 || this.#u(a)) && a.fn !== null) {
				s ? a.f ^= e : o & 4 ? n.push(a) : Jn(a) && _r(a);
				var c = a.first;
				if (c !== null) {
					a = c;
					continue;
				}
			}
			for (; a !== null;) {
				if ((a.f & 16512) == 128) {
					var l = a.b;
					l.is_pending && l.is_ready(this) && i.push(l);
				}
				var u = a.next;
				if (u !== null) {
					a = u;
					break;
				}
				a = a.parent;
			}
		}
	}
	#h() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#g(e)) return e;
		return null;
	}
	#g(e) {
		for (let t of this.current.keys()) if (e.current.has(t)) return !0;
		return !1;
	}
	#_(e) {
		for (let t of e.merge_requests) this.merge_requests.add(t);
		e.merge_requests.clear();
		for (let [t, n] of e.current) {
			if (!this.previous.has(t)) {
				let n = e.previous.get(t);
				n && this.previous.set(t, n);
			}
			this.current.set(t, n);
		}
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && e !== n && n.promise.then(e.resolve, e.reject), this.async_deriveds.set(t, n);
		}
		for (let [n, r] of e.records ?? []) if (!(n.f & 16)) {
			var t = this.records?.get(n);
			(this.records ??= /* @__PURE__ */ new Map()).set(n, r), e.records?.delete(n), Zn(n, t);
		}
		if (e.async_deriveds.clear(), e.#n.size > 0) {
			for (let [t, n] of e.#n) this.#n.set(t, (this.#n.get(t) ?? 0) + n);
			e.#n.clear();
		}
		if (e.#i.size > 0) {
			for (let [t, n] of e.#i) this.#v(t, n);
			e.#i.clear();
		}
		let n = () => e.discard();
		this.oncommit(n), this.ondiscard(n), e.merged = this, e.#T();
	}
	#v(e, t) {
		(t === 2048 || this.#i.get(e) !== 2048) && this.#i.set(e, t);
	}
	#y(r) {
		for (var i = 0; i < r.length; i += 1) {
			var a = r[i], o = a.f & (t | n);
			o !== 0 && (this.#v(a, a.dv === null ? n : o), D(a, e));
		}
	}
	capture(e, n, r, i = !1, a = null) {
		var o = this.previous.get(e), s = $t(this, e);
		o === void 0 && (o = s?.previous.get(e), o === void 0 && e.v !== y && (o = {
			v: e.v,
			wv: e.wv,
			e: (e.f & f) !== 0,
			assigned: (e.f & m) !== 0
		}), o !== void 0 && this.previous.set(e, o)), z ? Ft(e) : o !== void 0 && (M?.reverted_values.set(e, o), M?.derived_cache.clear());
		var c = {
			v: n,
			wv: r ? e.wv : Un(),
			e: i,
			assigned: !!(e.f & 2),
			async: (e.f & d) !== 0
		};
		this.current.set(e, c), N?.set(e, c), P?.delete(e), !this.is_fork && s !== null && s.previous.set(e, c), !this.is_fork && !r && s === null && en(e, c), r || (Ht = null, Ut = 0, this.mark(e, t, a), Ht = null, Ct.size > 0 && !wt && Ot());
	}
	deactivate() {
		j = Mt = N = P = F = null;
	}
	flush() {
		var e = Pt(this.previous);
		try {
			if (this.#f(), Lt.size > 0) for (let e of Lt) Lt.delete(e), e.linked && !e.#c && e.#f();
		} finally {
			Vt = 0, It = null, zt = null, Bt = null, M = e.parent, this.deactivate();
		}
	}
	discard() {
		this.#x(this.#t);
		for (let e of this.async_deriveds.values()) e.reject(pt);
		this.#T(), this.#r?.resolve();
	}
	#b() {
		for (let i = A; i !== null; i = i.next) if (i !== this) {
			var e = i.id < this.id, t = [];
			for (let [r, a] of this.current) {
				var n = i.current.get(r);
				if (n !== void 0) {
					if (e && a.v !== n.v && !n.async) i.current.set(r, a);
					else continue;
				}
				t.push(r);
			}
			if (i.started && i.current.size !== 0) {
				var r = !0;
				for (let e of i.current.keys()) if (!this.current.has(e)) {
					r = !1;
					break;
				}
				r && e ? i.discard() : t.length > 0 && (i.#p(t), Lt.add(i));
			}
		}
		this.current.clear(), this.previous.clear();
	}
	commit_writes() {
		this.#b(), this.linked && this.prev !== null && this.#w();
	}
	increment(e) {
		var t = this.#n.get(e) ?? 0;
		this.#n.set(e, t + 1);
	}
	decrement(e) {
		var t = this.#n.get(e) ?? 0;
		t === 1 ? this.#n.delete(e) : this.#n.set(e, t - 1), this.#c || (this.#c = !0, T(() => {
			this.#c = !1, this.linked && this.flush();
		}));
	}
	oncommit(e) {
		this.#e.set(e, Xt?.size ? Xt : null);
	}
	ondiscard(e) {
		this.#t.set(e, Xt?.size ? Xt : null);
	}
	#x(e) {
		Cr(() => {
			for (let [n, r] of e) if (r === null) n(this);
			else {
				var t = Pt();
				for (let [e, n] of r) t.reverted_values.has(e) && t.reverted_values.set(e, n);
				try {
					n(this);
				} finally {
					M = t.parent;
				}
			}
		}), e.clear();
	}
	settled() {
		return (this.#r ??= je()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new r();
			Mt === null && !Rt && T(() => {
				e.started || e.flush();
			});
		}
		return j;
	}
	activate() {
		j = this, F = this, Gt !== this.id && (Gt = null), N = P = null;
	}
	get_record(e) {
		for (var t = this.records?.get(e), n = this.folded.length; t === void 0 && n--;) t = this.folded[n].records?.get(e);
		return t;
	}
	mark(e, r, i = null) {
		var a = e.reactions;
		if (a !== null) {
			var o = Ze(), s = a.length;
			if (Ut += s, Ut > 1e5 && Ht === null && (Ht = /* @__PURE__ */ new Set()), Ht !== null) {
				if (Ht.has(e)) return;
				Ht.add(e);
			}
			for (var c = 0; c < s; c++) {
				var l = a[c], u = l.f;
				if (o || l !== U) {
					var d = (u & t) === 0;
					if (u & 131072) this.is_fork || (d && D(l, r), Ct.add(l));
					else if (u & 2) {
						d && D(l, r);
						var f = l;
						P?.delete(f), this.mark(f, n, i);
					} else if (d) {
						var p = l;
						u & 16 && Yt !== null && (D(p, r), Yt.add(p)), i === null ? this.schedule(p, r) : (D(p, r), i.push(p));
					}
				}
			}
		}
	}
	schedule(e, t) {
		if (It = e, F !== null && F !== this && e !== B) this.#v(e, e.f & 2097152 ? t : n);
		else {
			if (Mt !== this && B === null) {
				if (this.prev !== null || this.next !== null || this.is_fork) {
					this.#v(e, n);
					return;
				}
				t = n;
			}
			this.#S(e, t);
		}
	}
	#S(e, t) {
		e.f & 2048 || D(e, t), this.#a.push(e);
	}
	#C(e = !1) {
		var t = this.records;
		if (t !== null) {
			this.records = null;
			for (let [r, i] of t) {
				if (!(r.f & 16386)) {
					var n = !!(r.f & 4194304) && er(i) && !er(r);
					if (e && !n && (dr(r, i), r.f & 4194304)) for (let e = A; e !== null; e = e.next) e !== this && !e.records?.has(r) && e.async_deriveds.get(r)?.reject(pt);
					pr(r);
				}
				Zn(r, i);
			}
		}
	}
	#w() {
		var e = this.prev, t = A;
		e.next = this.next, this.next === null ? jt = e : this.next.prev = e, this.prev = null, this.next = t, t.prev = A = this, this.id = t.id - 1;
	}
	#T() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null ? A = t : e.next = t, t === null ? jt = e : t.prev = e, this.linked = !1, this.#C();
		}
	}
};
function qt(e) {
	var t = Rt, n = F === j ? null : F;
	Rt = !0;
	try {
		var r;
		for (e && (qt(), r = e());;) {
			if (et(), j === null) return r;
			j.flush();
		}
	} finally {
		Rt = t, F = n;
	}
}
function Jt() {
	try {
		Re();
	} catch (e) {
		Ne(e, It);
	}
}
var Yt = null, Xt = null;
function Zt(e) {
	if ((e.f & 32772) != 4) return !1;
	for (var t = e.b; t !== null; t = t.parent) if (t.is_pending) return t.defer_effect(e), !0;
	return !1;
}
function Qt(e, t = null) {
	var n = e.length;
	if (n === 0) return t;
	for (var r = 0; r < n;) {
		var i = e[r++];
		if (!(i.f & 24576) && !j?.is_skipped(i) && !Zt(i) && Jn(i)) {
			Yt = /* @__PURE__ */ new Set();
			var a = zn;
			if (_r(i), i.edges === null && i.first === null && i.nodes === null && i.teardown === null && i.ac === null && Sn(i), Yt?.size > 0) {
				var o = M;
				t !== null && Pt(t);
				var s = Xt;
				Xt = new Map(t);
				try {
					for (let e of Yt) {
						if (e.f & 24576 || j?.is_skipped(e)) continue;
						let t = [e], n = e.parent;
						for (; n !== null;) Yt.has(n) && (Yt.delete(n), t.push(n)), n = n.parent;
						for (let e = t.length - 1; e >= 0; e--) {
							let n = t[e];
							n.f & 24576 || j?.is_skipped(n) || _r(n);
						}
					}
				} finally {
					Xt = s, Yt?.clear(), M = o;
				}
			}
			if (zn !== a && j !== null) for (let [e, n] of j.current) n.wv > a && (t ??= /* @__PURE__ */ new Map()).set(e, n);
		}
	}
	return Yt = null, t;
}
function $t(e, t) {
	for (var n = e.next; n !== null && (n.is_fork || !n.current.has(t));) n = n.next;
	return n;
}
function en(e, t) {
	e.v = t.v, e.wv = t.wv, e.f = t.e ? e.f | f : e.f & ~f, e.f & 2 && (e.f |= m, dt(e));
}
function tn(e) {
	var t = N, n = P, r = F;
	N = P = F = null;
	try {
		e();
	} finally {
		N = t, P = n, F = r;
	}
}
function nn(t, n = !1) {
	if (!(!n && t.f & 32 && t.f & 1024)) {
		D(t, e);
		for (var r = t.first; r !== null;) nn(r, n), r = r.next;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function rn(e) {
	U === null && (B === null && Le(e), Ie()), z && Fe(e);
}
function an(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function I(e, n) {
	var i = U;
	i !== null && i.f & 8192 && (e |= r);
	var a = {
		ctx: w,
		deps: null,
		dv: null,
		edges: null,
		nodes: null,
		f: e | t | 512,
		first: null,
		fn: n,
		last: null,
		next: null,
		parent: i,
		b: i && i.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null,
		r: it
	}, s = a;
	if (e & 4) zt === null ? Kt.ensure().schedule(a, t) : zt.push(a);
	else if (n !== null) {
		try {
			_r(a);
		} catch (e) {
			throw R(a), e;
		}
		s.edges === null && s.teardown === null && s.nodes === null && s.first === s.last && !(s.f & 524288) && (s = s.first, e & 16 && e & 65536 && s !== null && (s.f |= o));
	}
	if (s !== null && (s.parent = i, i !== null && an(s, i), B !== null && B.f & 2 && !(e & 64))) {
		var c = B;
		(c.effects ??= []).push(s);
	}
	return a;
}
function on() {
	return B !== null && !V;
}
function sn(t) {
	let n = I(8, null);
	return D(n, e), n.teardown = t, n;
}
function cn(e) {
	rn("$effect");
	var t = U.f;
	if (!B && t & 32 && w !== null && !w.i) {
		var n = w;
		(n.e ??= []).push(e);
	} else return ln(e);
}
function ln(e) {
	return I(4 | c, e);
}
function un(e) {
	return rn("$effect.pre"), I(8 | c, e);
}
function dn(e) {
	Kt.ensure();
	let t = I(64 | s, e);
	return () => {
		R(t);
	};
}
function fn(e) {
	Kt.ensure();
	let t = I(64 | s, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Cn(t, () => {
			R(t), n(void 0);
		}) : (R(t), n(void 0));
	});
}
function pn(e) {
	return I(4, e);
}
function mn(e) {
	return I(d | s, e);
}
function hn(e, t = 0) {
	return I(8 | t, e);
}
function gn(e, t = [], n = [], r = []) {
	at(r, t, n, (t) => {
		I(8, () => {
			e(...t.map(Y));
		});
	});
}
function _n(e, t = 0) {
	return I(16 | t, e);
}
function L(e) {
	return I(32 | s, e);
}
function vn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = z, r = Nn, i = M, a = B;
		Pn(!0), H(null);
		try {
			t.call(null);
		} catch (t) {
			Ne(t, e.parent);
		} finally {
			Pn(n, r), Nt(i), H(a);
		}
	}
}
function yn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		nr(n);
		var r = n.next;
		n.f & 64 ? n.parent = null : R(n, t), n = r;
	}
}
function bn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || R(t), t = n;
	}
}
function R(e, t = !0) {
	var n = !1;
	try {
		(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (xn(e.nodes.start, e.nodes.end), n = !0), e.f |= a, yn(e, t && !n), gr(e);
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) e.stop();
		vn(e);
	} finally {}
	e.f ^= a, e.f |= 16384;
	var i = e.parent;
	i !== null && i.first !== null && Sn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.dv = e.edges = e.fn = e.nodes = e.ac = e.b = e.r = null;
}
function xn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Pr(e);
		Yr(e), e = n;
	}
}
function Sn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Cn(e, t, n = !0) {
	var r = [];
	e.f |= 256, wn(e, r, !0);
	var i = () => {
		n && R(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = M, s = () => {
			if (!--a) {
				var e = M;
				try {
					o && (o.derived_cache.clear(), Nt(o)), i();
				} finally {
					o && Nt(e);
				}
			}
		};
		for (var c of r) c.out(s);
	} else i();
}
function wn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= r;
		var i = e.nodes && e.nodes.t;
		if (i !== null) for (let e of i) (e.is_global || n) && t.push(e);
		for (var a = e.first; a !== null;) {
			var o = a.next;
			if (!(a.f & 64)) {
				var s = !!(a.f & 65536) || !!(a.f & 32) && !!(e.f & 16);
				wn(a, t, s ? n : !1);
			}
			a = o;
		}
	}
}
function Tn(e) {
	e.f &= -257, En(e, !0);
}
function En(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= r, e.f & 1024 || Kt.ensure().schedule(e, n);
		for (var i = e.first; i !== null;) {
			var a = i.next, o = !!(i.f & 65536) || !!(i.f & 32);
			En(i, o ? t : !1), i = a;
		}
		var s = e.nodes && e.nodes.t;
		if (s !== null) for (let e of s) (e.is_global || t) && e.in();
	}
}
function Dn(e, t) {
	if (e.nodes) try {
		for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
			var i = n === r ? null : /* @__PURE__ */ Pr(n);
			Kr(t, n), n = i;
		}
	} finally {}
}
// node_modules/svelte/src/internal/client/legacy.js
var On = null, kn = !1;
function An() {
	kn || (kn = !0, oi(document, "reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ae]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function jn(e) {
	var t = B, n = U;
	H(null), In(null);
	try {
		return e();
	} finally {
		H(t), In(n);
	}
}
function Mn(e, t, n, r = n) {
	e.addEventListener(t, () => jn(n));
	let i = e[ae];
	e[ae] = i ? () => {
		i(), r(!0);
	} : () => r(!0), An();
}
// node_modules/svelte/src/internal/client/runtime.js
var z = !1, Nn = 0;
function Pn(e, t = zn) {
	z = e, Nn = t;
}
var Fn = {
	v: void 0,
	wv: 0,
	e: !1,
	assigned: !1
}, B = null, V = !1;
function H(e) {
	B = e;
}
var U = null;
function In(e) {
	U = e;
}
var W = null;
function Ln(e) {
	B !== null && (B.f & 2097152 || B.f & 2) && (W ??= /* @__PURE__ */ new Set()).add(e);
}
var G = null, K = 0, q = null;
function Rn(e) {
	q = e;
}
var zn = 1, Bn = 0, Vn = Bn;
function Hn(e) {
	Vn = e;
}
function Un() {
	return ++zn;
}
function Wn(e) {
	return N === null ? (yt(e), e.wv) : e.f & 2 ? bt(e).wv : (N.get(e) ?? e).wv;
}
function Gn(e, t) {
	if (e !== null) {
		for (var n = 0; n < t.length; n++) if (Wn(e[n]) !== t[n]) return !1;
	}
	return !0;
}
function Kn(e, t, n = null) {
	if (e !== null) for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (i.f & 2) {
			var a = i;
			if (N === null ? yt(i) : a = bt(i), a.wv > t) {
				if (a === i ? i.f & 67108864 : !("dv" in a)) return !0;
				if (n === null) n = /* @__PURE__ */ new Set();
				else if (n.has(a)) continue;
				if (Kn(a.deps, t, n)) return !0;
				n.add(a);
			}
		} else if (Wn(i) > t) return !0;
	}
	return !1;
}
function qn(e) {
	return !!(e.f & 4194320) && F?.get_record(e) || e;
}
function Jn(t) {
	var n = t.f;
	if (!(n & 6144)) return !1;
	if (n & 67108864) {
		if (Kn(t.deps, t.wv)) return !0;
	} else if (n & 2048) return !0;
	else {
		var r = qn(t), i = r.deps, a = r.dv;
		if (a === null) return !0;
		if (N === null) for (var o = 0, s = a.length; o < s; o++) {
			var c = i[o];
			if (yt(c), c.wv !== a[o]) return !0;
		}
		else if (!Gn(i, a)) return !0;
	}
	return n & 512 && D(t, e), !1;
}
function Yn(e, r, i = !0) {
	var a = e.reactions;
	if (a !== null && !(W !== null && W.has(e))) for (var o = 0; o < a.length; o++) {
		var s = a[o];
		s.f & 2 ? Yn(s, r, !1) : r === s && j.schedule(s, i ? t : n);
	}
}
var J = null;
function Xn(e) {
	e && jn(() => e.abort(oe));
}
function Zn(e, t, n = !1) {
	if (t?.ac) {
		for (var r = A; r !== null; r = r.next) if (r.records?.get(e) === t && (!n || r !== F && !tr(j, r))) return;
		Xn(t.ac), t.ac = null;
	}
}
function Qn(e, t) {
	var n = j, r = !!(t & 2);
	if (!(r && z)) {
		var i = n === null || !n.is_fork;
		Zn(e, F?.records?.get(e), !0), (r ? N === null || i && er(e) : i) && Xn(e.ac);
		for (var a = A; a !== null; a = a.next) tr(n, a) && Zn(e, a.records?.get(e), !0);
	}
}
function $n(e) {
	Xn(e.ac), e.ac = J;
}
function er({ deps: e, dv: t }) {
	return t === null || t.some((t, n) => e[n].wv !== t);
}
function tr(e, t) {
	return e !== null && !e.is_fork && !t.is_fork && t.id < e.id && (N === null || t.previous.size === 0 || e.folded.includes(t));
}
function nr(e) {
	if (!(e.f & 134217728)) return !1;
	e.f ^= p, Xn(e.ac), e.ac = null;
	for (var t = A; t !== null; t = t.next) {
		var n = t.records?.get(e);
		n?.ac && (Xn(n.ac), n.ac = null);
	}
	return !0;
}
function rr(e) {
	return !(e & 4194304) && (e & 32784) != 32784 ? !1 : F !== null && F === j;
}
function ir(e) {
	let t = j;
	var n = G, r = K, a = q, o = B, s = W, c = w, l = V, d = Vn, f = e.f;
	G = null, K = 0, q = null, B = f & 96 ? null : e, W = null, qe(e.ctx), V = !1, Vn = ++Bn;
	var p = J;
	J = null, f & 134217728 && Qn(e, f);
	try {
		e.f |= u;
		var m = e.fn, h = m();
		if (e.f |= i, ar(e, f, h, !1), Ze() && q !== null && !V && (G !== null || K > 0) && !(e.f & 6146)) for (var g = 0; g < q.length; g++) Yn(q[g], e);
		if (o !== null && o !== e) {
			if (Bn++, o.deps !== null) for (let e = 0; e < r; e += 1) o.deps[e].rv = Bn;
			if (n !== null) for (let e of n) e.rv = Bn;
			q !== null && (a === null ? a = q : a.push(...q));
		}
		return h;
	} catch (t) {
		var _ = t;
		try {
			_ = Me(t);
		} finally {
			ar(e, f, _, _ === t);
		}
		return _;
	} finally {
		var ee = J?.signal;
		t !== null && ee !== void 0 && ee.addEventListener("abort", () => {
			if (j !== null) {
				let e = E(t);
				e !== j && e.linked && !e.is_fork && j.merge_requests.add(e);
			}
		}), e.f ^= u, G = n, K = r, q = a, B = o, W = s, qe(c), V = l, Vn = d, J = p;
	}
}
function ar(e, t, n, r) {
	var i = e.deps, a = K + (G === null ? 0 : G.length), o = e.dv;
	if (e.f & 16384) Xn(J);
	else if (J !== null && !(e.f & 134217728) && (Xn(J), J = null), t & 2 && z) {
		for (var s = 0, c = 0; c < a; c++) {
			var l = c < K ? i[c] : G[c - K];
			s = Math.max(s, Sr(l));
		}
		Fn = {
			v: n,
			wv: s,
			e: r,
			assigned: (t & m) !== 0
		};
	} else if (t & 2 && N === null && A !== null && A.next !== null && cr(e, t), G === null && N === null && o !== null && a === i?.length && e.edges === i && !(t & 4194320)) {
		for (var u = 0; u < a; u++) o[u] = i[u].wv;
		o.length !== a && (o.length = a), t & 2 && or(e, n, r), (e.ac || J) && $n(e);
	} else sr(e, t, a, n, r);
}
function or(e, t, n) {
	var r = e.f & ~m;
	(n || r & 8388608 || !e.equals(t)) && (e.v = t, e.wv = Un(), r = n ? r | f : r & ~f), e.f = r, dt(e);
}
function sr(e, t, n, r, i) {
	var a = rr(t);
	if (N !== null && t & 2) {
		var o = N.get(e);
		o !== void 0 && o.wv !== e.wv && (a = !0);
	}
	var s = e.deps, c = s;
	(G !== null || K !== s?.length) && (c = K === 0 ? G : s.slice(0, K).concat(G ?? []));
	for (var l = !a && N === null && e.dv !== null ? e.dv : [], u = 0; u < n; u++) {
		var d = c[u];
		l[u] = lr(d), N !== null && t & 2 && (l[u] !== d.wv || (d.f & 1026) == 2) && (a = !0);
	}
	l.length !== n && (l.length = n), !a && N !== null && t & 2 && cr(e, t);
	var f = a || fr(e), p = on() && !!(e.f & 512), m = e.edges;
	if (f && m !== null) {
		if (G !== null) {
			e.edges = m = m.slice();
			for (d of G) ve.call(m, d) || (m.push(d), p && (d.reactions ??= []).push(e));
		}
	} else {
		if (m === s) {
			if (m !== null) for (u = K; u < m.length; u++) hr(e, m[u]);
			if (p && G !== null) for (d of G) (d.reactions ??= []).push(e);
		} else {
			var h = new Set(c);
			for (d of m) h.delete(d) || hr(e, d);
			if (p) for (d of h) (d.reactions ??= []).push(e);
		}
		e.edges = c;
	}
	if (a) {
		var g = F;
		(g.records ??= /* @__PURE__ */ new Map()).set(e, t & 2 ? {
			deps: c,
			dv: l,
			v: r,
			e: i,
			wv: ur(e, g, r, i),
			ac: J
		} : {
			deps: c,
			dv: l,
			ac: J
		});
	} else e.deps = c, e.dv = l, (e.ac || J) && $n(e), t & 2 && (or(e, r, i), F?.records?.delete(e));
}
function cr(e, t) {
	var n = e.dv;
	if (!(n === null || n.length === 0 || t & 67108864)) {
		for (var r, i = e.ac, a = i !== null && j !== null && j.is_fork && !i.signal.aborted, o = A; o !== null; o = o.next) o !== F && !o.records?.has(e) && (i === null || a || tr(j, o)) && (r ??= {
			deps: e.deps,
			dv: n.slice(),
			v: e.v,
			wv: e.wv,
			e: (t & f) !== 0
		}, (o.records ??= /* @__PURE__ */ new Map()).set(e, r));
		a && r !== void 0 && (r.ac = i, e.ac = null);
	}
}
function lr(e) {
	return N === null ? e.wv : e.f & 2 ? P.get(e)?.wv ?? -1 : (N.get(e) ?? e).wv;
}
function ur(e, t, n, r) {
	if (!r) {
		var i = t.get_record(e);
		if (i !== void 0 && !i.e && e.equals.call(i, n)) return i.wv;
		if (!(e.f & 8388608) && e.equals(n)) return e.wv;
	}
	return Un();
}
function dr(e, t) {
	if (e.deps = t.deps, e.dv = e.f & 2 ? t.dv.slice() : t.dv, e.f & 2) {
		var n = e;
		n.v = t.v, n.wv = t.wv, n.f = (t.e ? n.f | f : n.f & ~f) & ~m, dt(n);
	}
	Xn(e.ac), e.ac = t.ac ?? null, t.ac = null;
}
function fr(e) {
	for (var t = A; t !== null; t = t.next) if (t.records?.has(e)) return !0;
	return !1;
}
function pr(e) {
	var t = e.edges, n = e.deps;
	if (!(t === n || fr(e))) {
		for (var r of t) n !== null && ve.call(n, r) || hr(e, r);
		e.edges = n;
	}
}
function mr(e, t) {
	var n = e.reactions ??= [];
	ve.call(n, t) || n.push(t);
}
function hr(e, n) {
	let r = n.reactions;
	if (r !== null) {
		var i = _e.call(r, e);
		if (i !== -1) {
			var a = r.length - 1;
			a === 0 ? r = n.reactions = null : (r[i] = r[a], r.pop());
		}
	}
	if (r === null && n.f & 2 && (G === null || !ve.call(G, n))) {
		var o = n;
		if (o.f & 512 && (o.f ^= 512), o.v !== y && dt(o), nr(o)) {
			D(o, t), o.dv = null;
			for (var s = A; s !== null; s = s.next) s.records?.delete(o);
			P?.delete(o);
		}
		xt(o), gr(o);
	}
}
function gr(e) {
	var t = e.edges;
	if (t !== null) for (var n = 0; n < t.length; n++) hr(e, t[n]);
}
function _r(t) {
	var n = t.f;
	if (!(n & 16384)) {
		D(t, e);
		var r = U;
		U = t;
		try {
			n & 16777232 ? bn(t) : yn(t), vn(t);
			var i = ir(t);
			t.teardown = typeof i == "function" ? i : null, t.wv = zn;
		} finally {
			U = r;
		}
	}
}
async function vr() {
	await Promise.resolve(), qt();
}
function Y(e) {
	var t = !!(e.f & 2);
	On?.add(e);
	var n = null;
	if (B !== null && !V && !(U !== null && U.f & 16384) && (W === null || !W.has(e))) {
		var r = B.deps;
		if (B.f & 2097152) e.rv < Bn && (e.rv = Bn, G === null && r !== null && r[K] === e ? K++ : G === null ? G = [e] : G.push(e));
		else {
			n = B;
			var a = B.edges;
			a !== null && ve.call(a, e) || (B.edges = a === null ? [e] : [...a, e]), mr(e, B);
		}
	}
	if (z) {
		var o = xr(e);
		if (o !== void 0) {
			if (o.e) throw o.v;
			return o.v;
		}
	}
	var s;
	if (t) {
		var c = e, l = !(c.f & 512) && !V && B !== null && !!(B.f & 512), u = !(c.f & i);
		l && (c.f |= 512), N === null ? yt(c) : s = bt(c), l && !u && (St(c), br(c));
	} else N !== null && (s = N.get(e));
	if (n !== null && yr(n, e, s === void 0 ? e.wv : s.wv), s !== void 0 && s !== e) {
		if (s.e) throw s.v;
		return s.v;
	}
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function yr(e, t, n) {
	var r = qn(e), i = r.deps;
	r.dv === null || i !== null && ve.call(i, t) || (r.deps = i === null ? [t] : [...i, t], r.dv.push(n));
}
function br(e) {
	if (e.f |= 512, e.edges !== null) for (let t of e.edges) mr(t, e), t.f & 2 && !(t.f & 512) && (St(t), br(t));
}
function xr(e) {
	var t = e.wv > Nn ? void 0 : M?.reverted_values.get(e);
	if (!(e.f & 2)) return t;
	var n = e, r = (M ?? Pt()).derived_cache, i = r.get(n);
	if (i !== void 0) return i;
	var a = t ?? N?.get(n), o = a === void 0 ? (n.f & m) !== 0 : a.assigned, s = a === void 0 && !o ? n.dv : null, c = n.deps ?? [], l = o || s !== null, u = s?.length ?? c.length;
	a ??= {
		v: n.v,
		wv: n.wv,
		e: (n.f & f) !== 0,
		assigned: (n.f & m) !== 0
	};
	for (var d = 0; l && d < u; d++) {
		var p = Sr(c[d]);
		l = s === null ? p <= a.wv : p === s[d];
	}
	return l ? i = a : (vt(n), i = Fn, a.wv < i.wv && !a.e && !i.e && n.equals.call(a, i.v) && (i.wv = a.wv)), r.set(n, i), i;
}
function Sr(e) {
	return (xr(e) ?? N?.get(e) ?? e).wv;
}
function Cr(e) {
	var t = V;
	try {
		return V = !0, e();
	} finally {
		V = t;
	}
}
function wr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (h in e) Tr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && h in n && Tr(n);
		}
	}
}
function Tr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Tr(e[n], t);
		} catch {}
		let n = Ee(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = Ce(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function Er(e) {
	if (typeof e != "object" || !e || h in e || g in e) return e;
	let t = Ee(e);
	if (t !== we && t !== Te) return e;
	var n = /* @__PURE__ */ new Map(), r = ge(e), i = /* @__PURE__ */ Et(0), a = null, o = Vn, s = (e) => {
		if (Vn === o) return e();
		var t = B, n = Vn;
		H(null), Hn(o);
		var r = e();
		return H(t), Hn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Et(e.length, a)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Ve();
			var i = n.get(t);
			return i === void 0 ? s(() => {
				var e = /* @__PURE__ */ Et(r.value, a);
				return n.set(t, e), e;
			}) : k(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = s(() => /* @__PURE__ */ Et(y, a));
					n.set(t, e), At(i);
				}
			} else k(r, y), At(i);
			return !0;
		},
		get(t, r, i) {
			if (r === h) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || Se(t, r)?.writable) && (o = s(() => /* @__PURE__ */ Et(Er(c ? t[r] : y), a)), n.set(r, o)), o !== void 0) {
				var l = Y(o);
				return l === y ? void 0 : l;
			}
			return Reflect.get(t, r, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var r = Reflect.getOwnPropertyDescriptor(e, t), i = n.get(t);
			if (i !== void 0) {
				var a = Y(i);
				if (a === y) return;
				if (r && "value" in r) r.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === h) return !0;
			var r = n.get(t), i = r !== void 0 && r.v !== y || Reflect.has(e, t);
			return (r !== void 0 || (U !== null || B !== null) && (!i || Se(e, t)?.writable)) && (r === void 0 && (r = s(() => /* @__PURE__ */ Et(i ? Er(e[t]) : y, a)), n.set(t, r)), Y(r) === y) ? !1 : i;
		},
		set(e, t, o, c) {
			var l = n.get(t), u = t in e;
			if (r && t === "length") for (var d = o; d < l.v; d += 1) {
				var f = n.get(d + "");
				f === void 0 ? d in e && (f = s(() => /* @__PURE__ */ Et(y, a)), n.set(d + "", f)) : k(f, y);
			}
			if (l === void 0) (!u || Se(e, t)?.writable) && (l = s(() => /* @__PURE__ */ Et(void 0, a)), k(l, Er(o)), n.set(t, l));
			else {
				u = l.v !== y;
				var p = s(() => Er(o));
				k(l, p);
			}
			var m = Reflect.getOwnPropertyDescriptor(e, t);
			if (m?.set && m.set.call(c, o), !u) {
				if (r && typeof t == "string") {
					var h = n.get("length"), g = Number(t);
					Number.isInteger(g) && g >= h.v && k(h, g + 1);
				}
				At(i);
			}
			return !0;
		},
		ownKeys(e) {
			Y(i);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== y;
			});
			for (var [r, a] of n) a.v !== y && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			He();
		}
	});
}
var Dr, Or, kr, Ar;
function jr() {
	if (Dr === void 0) {
		Dr = window, Or = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		kr = Se(t, "firstChild").get, Ar = Se(t, "nextSibling").get, De(e) && (e[ne] = void 0, e[te] = null, e[re] = void 0, e.__e = void 0), De(n) && (n[ie] = void 0);
	}
}
function Mr(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Nr(e) {
	return kr.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Pr(e) {
	return Ar.call(e);
}
function X(e, t) {
	if (!b) return /* @__PURE__ */ Nr(e);
	var n = /* @__PURE__ */ Nr(x);
	if (n === null) n = Kr(x, Mr());
	else if (t && Hr(n) !== 3) {
		var r = Mr();
		return qr(n, r), S(r), r;
	}
	return t && Vr(n), S(n), n;
}
function Fr(e, t = !1) {
	if (!b) return /* @__PURE__ */ Nr(e);
	var n = X(e, t);
	return C(e), n;
}
function Z(e, t = 1, n = !1) {
	let r = b ? x : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Pr(r);
	if (!b) return r;
	if (n) {
		if (Hr(r) !== 3) {
			var a = Mr();
			return r === null ? i && Jr(i, a) : qr(r, a), S(a), a;
		}
		Vr(r);
	}
	return S(r), r;
}
function Ir(e) {
	e.textContent = "";
}
function Lr() {
	return Xt !== null && !!(U.f & i);
}
function Rr(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function zr() {
	return document.createDocumentFragment();
}
function Br(e, t, n = "") {
	if (t.startsWith("xlink:")) e.setAttributeNS("http://www.w3.org/1999/xlink", t, n);
	else return e.setAttribute(t, n);
}
function Vr(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && Hr(t) === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Hr(e) {
	if (e != null) return e.nodeType;
}
function Ur(e) {
	return e.nodeName;
}
function Wr(e) {
	return e.lastChild;
}
function Gr(e) {
	return e.parentNode;
}
function Kr(e, t) {
	return e.appendChild(t);
}
function qr(e, t) {
	e.before(t);
}
function Jr(e, t) {
	e.after(t);
}
function Yr(e) {
	e.remove();
}
function Xr(e, t) {
	return e.removeChild(t);
}
function Zr(e, t) {
	e.textContent = t;
}
function Qr(e, t) {
	e.nodeValue = t;
}
function $r(e) {
	return e.nodeValue;
}
function ei(e, t) {
	return e.getAttribute(t);
}
function ti(e, t) {
	e.removeAttribute(t);
}
function ni(e, t) {
	return e.hasAttribute(t);
}
function ri(e, t) {
	e.innerHTML = t;
}
function ii(e, t) {
	return e.cloneNode(t);
}
function ai(e, t) {
	return document.importNode(e, t);
}
function oi(e, t, n, r) {
	e.addEventListener(t, n, r);
}
function si(e, t, n, r) {
	e.removeEventListener(t, n, r);
}
// node_modules/svelte/src/internal/flags/legacy.js
jr(), typeof window < "u" && ((globalThis.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5"), Ke(), [.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var ci = ["touchstart", "touchmove"];
function li(e) {
	return ci.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var ui = Symbol("events"), di = Symbol("propagation stopped at"), fi = /* @__PURE__ */ new Set(), pi = /* @__PURE__ */ new Set();
function mi(e, t, n, r = {}) {
	var i = it != null;
	function a(...e) {
		if (i) return jn(() => n?.apply(this, e));
		var a = e[0];
		if (r.capture || bi.call(t, a), r.capture || a[di] !== t) return jn(() => n?.call(this, a));
	}
	return !i && (e.startsWith("pointer") || e.startsWith("touch") || e === "wheel") ? (a.__removed = !1, T(() => {
		a.__removed || oi(t, e, a, r);
	})) : oi(t, e, a, r), a;
}
function hi(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = mi(e, t, n, a);
	it == null && (t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && sn(() => {
		o.__removed = !0, si(t, e, o, a);
	});
}
var gi = /* @__PURE__ */ new Map();
function _i(e) {
	var t = /* @__PURE__ */ new Set(), n = (n) => {
		for (var r = 0; r < n.length; r++) {
			var i = n[r];
			if (!t.has(i)) {
				t.add(i);
				var a = li(i);
				for (let t of [e, document]) {
					var o = gi.get(t);
					o === void 0 && (o = /* @__PURE__ */ new Map(), gi.set(t, o));
					var s = o.get(i);
					s === void 0 ? (t.addEventListener(i, bi, { passive: a }), o.set(i, 1)) : o.set(i, s + 1);
				}
			}
		}
	};
	return n(ye(fi)), pi.add(n), () => {
		for (var r of t) for (let t of [e, document]) {
			var i = gi.get(t), a = i.get(r);
			--a == 0 ? (t.removeEventListener(r, bi), i.delete(r), i.size === 0 && gi.delete(t)) : i.set(r, a);
		}
		pi.delete(n);
	};
}
var vi = null, yi = !1;
function bi(e) {
	var t = this, n = e.cancelBubble;
	if (!(n && e[di] === t)) {
		n || delete e[di];
		var r = t.ownerDocument, i = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
		vi = e, yi || (yi = !0, setTimeout(() => {
			yi = !1, vi = null;
		}));
		var s = 0, c = vi === e && e[ui];
		if (c) {
			var l = a.indexOf(c);
			if (l !== -1 && (t === document || t === window)) {
				e[ui] = t;
				return;
			}
			var u = a.indexOf(t);
			if (u === -1) return;
			l <= u && (s = l);
		}
		if (o = a[s] || e.target, o !== t) {
			xe(e, "currentTarget", {
				configurable: !0,
				get() {
					return o || r;
				}
			});
			var d = B, f = U;
			H(null), In(null);
			try {
				for (var p, m = []; o !== null && o !== t;) {
					try {
						var h = o[ui]?.[i];
						h == null || o.disabled && e.target !== o || h.call(o, e);
					} catch (e) {
						p ? m.push(e) : p = e;
					}
					if (e.cancelBubble) {
						n || (e[di] = t);
						break;
					}
					s++, o = s < a.length ? a[s] : null;
				}
				if (p) {
					for (let e of m) queueMicrotask(() => {
						throw e;
					});
					throw p;
				}
			} finally {
				e[ui] = t, delete e.currentTarget, H(d), In(f);
			}
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var xi = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Si(e) {
	return xi?.createHTML(e) ?? e;
}
function Ci(e) {
	var t = Rr("template");
	return ri(t, Si(e.replaceAll("<!>", "<!---->"))), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function wi(e, t) {
	var n = U;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (b) return wi(x, null), x;
		i === void 0 && (i = Ci(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Nr(i)));
		var t = r || Or ? ai(i, !0) : ii(i, !0);
		return n ? wi(/* @__PURE__ */ Nr(t), Wr(t)) : wi(t, t), t;
	};
}
function $(e, t) {
	if (b) {
		var n = U;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = x), fe();
	} else e !== null && qr(e, t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function Ti(e) {
	let t = 0, n = Tt(0), r;
	return () => {
		on() && (Y(n), hn(() => (t === 0 && (r = Cr(() => e(() => At(n)))), t += 1, () => {
			T(() => {
				--t, t === 0 && (r?.(), r = void 0, At(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ei = o | s;
function Di(e, t, n, r) {
	new Oi(e, t, n, r);
}
var Oi = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = b ? x : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = !1;
	#d = [];
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = Ti(() => (this.#p = Tt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = U;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = U.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = _n(() => {
			if (b) {
				let e = he(this.#t);
				fe();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, Ei), b && (this.#e = x);
	}
	#h() {
		try {
			this.#a = L(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		T(r), t && (this.#s = L(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? ue() : (t = !0, n && We(), this.#s !== null && Cn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					Ne(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return !!(this.#i.f & 33570816);
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = L(() => e(this.#e)), T(() => {
			if (!this.#v()) try {
				var e = this.#c = zr(), t = Mr();
				Kr(e, t), this.#a = this.#x(() => {
					try {
						return L(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e);
						} catch (e) {
							Ne(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a !== null && this.#f.size === 0 && (this.is_pending = !1, qr(this.#e, e), this.#c = null, Cn(this.#o, () => {
					this.#o = null;
				}));
			} finally {}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#l = 0, this.#a = L(() => {
				this.#r(this.#e);
			}), this.#f.size === 0) this.is_pending = !1;
			else {
				let t = this.#n.pending;
				if (t) {
					var e = this.#c = zr();
					Dn(this.#a, e), this.#o = L(() => t(this.#e));
				}
			}
		} catch (e) {
			this.error(e);
		}
	}
	defer_effect(e) {
		this.#d.push(e);
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = U, n = B, r = w;
		In(this.#i), H(this.#i), qe(this.#i.ctx);
		try {
			return Kt.ensure(), e();
		} finally {
			In(t), H(n), qe(r);
		}
	}
	is_ready(e) {
		if (e.is_fork && this.#f.size > 0) return !1;
		for (let [t, n] of this.#f) if (!t.is_fork) {
			for (let t of n.keys()) if (e.is_blocked_by(t, this.#a)) return !1;
		}
		return !0;
	}
	reveal(e) {
		this.is_pending = !1;
		for (let n of this.#d) D(n, t), e.push(n);
		if (this.#d.length = 0, this.#o && Cn(this.#o, () => {
			this.#o = null;
		}), this.#c) try {
			qr(this.#e, this.#c), this.#c = null;
		} finally {}
	}
	increment(e, t) {
		var n = this.#f.get(t);
		n === void 0 && this.#f.set(t, n = /* @__PURE__ */ new Map());
		var r = n.get(e) ?? 0;
		n.set(e, r + 1);
	}
	decrement(e, t) {
		var r = this.#f.get(t), i = r.get(e);
		i === 1 ? (r.delete(e), r.size === 0 && this.#f.delete(t), T(() => {
			this.is_pending && !this.#v() && Kt.ensure().schedule(this.#i, n);
		})) : r.set(e, i - 1);
	}
	update_effect_pending(e) {
		this.#l += e, !this.#p || this.#u || (this.#u = !0, T(() => {
			this.#u = !1, this.#p && Dt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Y(this.#p);
	}
	error(e) {
		if (e === v || !this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.oncommit(() => {
			this.#v() || this.#S(e);
		})) : this.#S(e);
	}
	#S(e) {
		this.#a &&= (R(this.#a), null), this.#o &&= (R(this.#o), null), this.#s &&= (R(this.#s), null), b && (S(this.#t), pe(), S(me()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#x(() => {
				try {
					return L(() => {
						var r = U;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return Ne(e, this.#i.parent), null;
				}
			}));
		};
		T(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					Ne(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => Ne(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function ki(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ie] ??= $r(e)) && (e[ie] = n, Qr(e, `${n}`));
}
function Ai(e, t) {
	return Mi(e, t);
}
function ji(e, t) {
	t.intro = t.intro ?? !1;
	let n = t.target, r = b, i = x;
	try {
		for (var a = /* @__PURE__ */ Nr(n); a && (Hr(a) !== 8 || $r(a) !== "[");) a = /* @__PURE__ */ Pr(a);
		if (!a) throw v;
		de(!0), S(a);
		let r = Mi(e, {
			...t,
			anchor: a
		});
		return de(!1), r;
	} catch (r) {
		if (r instanceof Error && r.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw r;
		return r !== v && console.warn("Failed to hydrate: ", r), t.recover === !1 && ze(), Ir(n), de(!1), Ai(e, t);
	} finally {
		de(r), S(i);
	}
}
function Mi(e, t) {
	return Ni(e, t);
}
function Ni(e, { target: t, anchor: n, props: r = {}, events: i, context: a, intro: o = !0, transformError: s, renderer: c }) {
	var l = void 0, u = fn(() => {
		var o = n ?? Kr(t, Mr());
		Di(o, { pending: () => {} }, (t) => {
			Je({});
			var n = w;
			if (a && (n.c = a), i && (r.$$events = i), b && wi(t, null), l = e(t, r) || Xe(), b && (U.nodes.end = x, x === null || Hr(x) !== 8 || $r(x) !== "]")) throw le(), v;
			Ye();
		}, s);
		var u = c ? null : _i(t);
		return () => {
			if (u?.(), o !== n) {
				var e = Gr(o);
				e && Xr(e, o);
			}
		};
	});
	return Pi.set(l, u), l;
}
var Pi = /* @__PURE__ */ new WeakMap();
function Fi(e, t) {
	let n = Pi.get(e);
	return n ? (Pi.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Ii = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	#a = null;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t, this.#a = it;
	}
	#o = (e) => {
		if (this.#e.has(e)) try {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Tn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Tn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), Yr(Wr(r.fragment)), qr(this.anchor, r.fragment), n = r.effect, n.f &= ~l);
			}
			this.#s(e);
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = zr();
						Dn(r, t), Kr(t, Mr()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else R(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Cn(r, i, !1)) : i();
			}
		} finally {}
	};
	#s = (e) => {
		for (let t of this.#e.keys()) t !== e && t.linked || this.#e.delete(t);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (R(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = Lr();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = zr(), a = Mr();
				Kr(i, a);
				var o = L(() => t(a));
				o.f |= l, n.unskip_new_effect(o), this.#n.set(e, {
					effect: o,
					fragment: i
				});
			} else this.#t.set(e, L(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#o), n.ondiscard(this.#s);
		} else b && (this.anchor = x), this.#o(n);
	}
};
function Li(e) {
	w === null && Pe("onMount"), Ge && w.l !== null ? Ri(w).m.push(e) : cn(() => {
		let t = Cr(e);
		if (typeof t == "function") return t;
	});
}
function Ri(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function zi(e, t, n = !1) {
	var r;
	b && (r = x, fe());
	var i = new Ii(e), a = n ? o : 0;
	function s(e, t) {
		if (b) {
			var n = he(r);
			if (e !== parseInt(n.substring(1))) {
				var a = me();
				S(a), i.anchor = a, de(!1), i.ensure(e, t), de(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	_n(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, s(n, t);
		}), e || s(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/client/dom/css.js
function Bi(e, t) {
	pn(() => {
		e = U?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = Rr("style");
			e.id = t.hash, Zr(e, t.code), Kr(r, e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Vi = Symbol("is custom element"), Hi = Symbol("is html"), Ui = se ? "link" : "LINK";
function Wi(e) {
	if (b) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, ni(e, "value")) {
					var n = e.value;
					Gi(e, "value", null), e.value = n;
				}
				if (ni(e, "checked")) {
					var r = e.checked;
					Gi(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ae] = n, T(n), An();
	}
}
function Gi(e, t, n, r) {
	var i = Ki(e);
	if (!(b && (i[t] = ei(e, t), t === "src" || t === "srcset" || t === "href" && Ur(e) === Ui))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[ee] = n), n == null ? ti(e, t) : typeof n != "string" && Ji(e).has(t) ? e[t] = n : (!b || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && Br(e, t, n));
	}
}
function Ki(e) {
	return e[te] ??= {
		[Vi]: Ur(e).includes("-"),
		[Hi]: it == null && e.namespaceURI === "http://www.w3.org/1999/xhtml"
	};
}
var qi = /* @__PURE__ */ new Map();
function Ji(e) {
	var t = ei(e, "is") || Ur(e), n = qi.get(t);
	if (n) return n;
	qi.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = Ce(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = Ee(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Yi(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	Mn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Xi(e) ? Zi(a) : a, n(a), j !== null && r.add(j), await vr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (b && e.defaultValue !== e.value || Cr(t) == null && e.value) && (n(Xi(e) ? Zi(e.value) : e.value), j !== null && r.add(j)), hn(() => {
		var n = t();
		e === document.activeElement && r.has(F) || Xi(e) && n === Zi(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function Xi(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Zi(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Qi(e = !1) {
	let t = w, n = t.l.u;
	if (!n) return;
	let r = () => wr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ ft(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && un(() => {
		$i(t, r), Ae(n.b);
	}), cn(() => {
		let e = Cr(() => n.m.map(ke));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && cn(() => {
		$i(t, r), Ae(n.a);
	});
}
function $i(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var ea = !1;
function ta(e) {
	var t = ea;
	try {
		return ea = !1, [e(), ea];
	} finally {
		ea = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function na(e, t, n, r) {
	var i = !Ge || !!(n & 2), a = !!(n & 8), o = !!(n & 16), s = r, c = !0, l = void 0, u = () => o && i ? (l ??= /* @__PURE__ */ ft(r), Y(l)) : (c && (c = !1, s = o ? Cr(r) : r), s);
	let d;
	if (a) {
		var f = h in e || _ in e;
		d = Se(e, t)?.set ?? (f && t in e ? (n) => e[t] = n : void 0);
	}
	var p, m = !1;
	a ? [p, m] = ta(() => e[t]) : p = e[t], p === void 0 && r !== void 0 && (p = u(), d && (i && Be(t), d(p)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? u() : (c = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (s = void 0), n === void 0 ? s : n;
	};
	if (i && !(n & 4)) return g;
	if (d) {
		var ee = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || ee || m) && d(t ? g() : e), e) : g();
		});
	}
	var te = !1, ne = (n & 1 ? ft : gt)(() => (te = !1, g()));
	a && Y(ne);
	var re = U;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(ne) : i && a ? Er(e) : e;
			return k(ne, n), te = !0, s !== void 0 && (s = n), e;
		}
		return z && te || re.f & 16384 ? ne.v : Y(ne);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function ra(e) {
	return new ia(e);
}
var ia = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ O(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Y(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === _ || (Y(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return k(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		}), i = {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		};
		this.#t = e.hydrate ? ji(e.component, i) : Ai(e.component, i), e?.props?.$$host && e.sync !== !1 || qt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && xe(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Fi(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, aa;
typeof HTMLElement == "function" && (aa = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = Rr("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = sa(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = oa(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ra({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = dn(() => {
				hn(() => {
					this.$$r = !0;
					for (let e of be(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = oa(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = oa(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return be(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function oa(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function sa(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ca(e, t, n, r, i, a) {
	let o = class extends aa {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return be(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return be(t).forEach((e) => {
		xe(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = oa(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (Se(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		xe(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
// PlexCard.svelte
var la = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-lueg2f\">Active</span>"), ua = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Authenticated</span>"), da = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Connected</span>"), fa = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-lueg2f\">Disconnected</span>"), pa = /* @__PURE__ */ Q("<div class=\"loading-state svelte-lueg2f\"><div class=\"spinner svelte-lueg2f\"></div> <span>Linking with Plex Nexus...</span></div>"), ma = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\"> </button>"), ha = /* @__PURE__ */ Q("<button class=\"btn-ghost accent svelte-lueg2f\"> </button>"), ga = /* @__PURE__ */ Q("<button class=\"btn-danger-ghost svelte-lueg2f\">Cancel Authorization</button>"), _a = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\">Switch Account</button>"), va = /* @__PURE__ */ Q("<button class=\"btn-primary plex-btn svelte-lueg2f\"><svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z\"></path></svg> Sign in with Plex</button>"), ya = /* @__PURE__ */ Q("<div class=\"settings-section svelte-lueg2f\"><div class=\"form-grid svelte-lueg2f\"><div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Server Access URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input-field svelte-lueg2f\"/> <span class=\"helper-text svelte-lueg2f\">Typically http://[IP]:32400. Use localhost if running natively.</span></div> <div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Friendly Name</span> <input type=\"text\" placeholder=\"e.g. Home Media\" class=\"input-field svelte-lueg2f\"/></div> <div class=\"actions-row svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <div class=\"auth-box svelte-lueg2f\"><!></div></div></div></div>"), ba = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"card-title svelte-lueg2f\">Plex Media Server</h2> <div class=\"badges svelte-lueg2f\"><!> <!> <!></div></div> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <!></section>"), xa = {
	hash: "svelte-lueg2f",
	code: "\n  /* SHADOW DOM STYLING */.plugin-card.svelte-lueg2f {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;color:var(--text-primary);font-family:inherit;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:16px;}.card-title.svelte-lueg2f {margin:0;font-size:18px;font-weight:700;letter-spacing:-0.01em;}.badges.svelte-lueg2f {display:flex;gap:8px;}.status-badge.svelte-lueg2f {font-size:9px;padding:2px 8px;border-radius:5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;}.status-badge.active.svelte-lueg2f {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-lueg2f {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-lueg2f {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-lueg2f,\n  .btn-ghost-small.svelte-lueg2f,\n  .btn-danger-ghost.svelte-lueg2f {padding:10px 18px;background:rgba(255, 255, 255, 0.04);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-ghost-small.svelte-lueg2f {padding:6px 12px;font-size:11px;border-radius:6px;}.btn-ghost.svelte-lueg2f:hover,\n  .btn-ghost-small.svelte-lueg2f:hover {background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.2);}.btn-ghost.accent.svelte-lueg2f {color:var(--color-primary);border-color:rgba(20, 184, 166, 0.3);}.btn-danger-ghost.svelte-lueg2f {color:#ef4444;border-color:rgba(239, 68, 68, 0.2);}.btn-primary.svelte-lueg2f {padding:10px 24px;background:var(--color-primary);color:#000;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-1px);}.plex-btn.svelte-lueg2f {display:flex;align-items:center;gap:8px;background:#e5a00d; /* Plex Gold */color:#000;}.loading-state.svelte-lueg2f {display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);}.spinner.svelte-lueg2f {width:28px;height:28px;border:3px solid rgba(255, 255, 255, 0.05);border-top-color:var(--color-primary);border-radius:50%;\n    animation: svelte-lueg2f-spin 1s linear infinite;}\n\n  @keyframes svelte-lueg2f-spin {\n    to {\n      transform: rotate(360deg);\n    }\n  }.settings-section.svelte-lueg2f {margin-top:8px;}.form-grid.svelte-lueg2f {display:flex;flex-direction:column;gap:20px;}.form-field.svelte-lueg2f {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-lueg2f {font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;}.input-field.svelte-lueg2f {width:100%;padding:12px 16px;background:var(--bg-input, #0b0f1a);border:1px solid var(--border-subtle);border-radius:10px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-lueg2f:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 3px rgba(20, 184, 166, 0.1);}.helper-text.svelte-lueg2f {font-size:11px;color:var(--text-muted);font-style:italic;}.actions-row.svelte-lueg2f {display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px;}.auth-box.svelte-lueg2f {margin-left:auto;}\n\n  @media (max-width: 600px) {.auth-box.svelte-lueg2f {margin-left:0;width:100%;}.auth-box.svelte-lueg2f button:where(.svelte-lueg2f) {width:100%;}\n  }"
};
function Sa(e, t) {
	Je(t, !1), Bi(e, xa);
	let n = na(t, "apiBase", 12, ""), r = /* @__PURE__ */ O(""), i = /* @__PURE__ */ O(""), a = /* @__PURE__ */ O(!1), o = /* @__PURE__ */ O(!1), s = /* @__PURE__ */ O(!0), c = /* @__PURE__ */ O(!1), l = /* @__PURE__ */ O(!1), u = /* @__PURE__ */ O(!1), d = null, f = null, p = /* @__PURE__ */ O(!1), m = /* @__PURE__ */ O(!1), h = /* @__PURE__ */ O(!1);
	Li(async () => {
		n(n().replace(/\/$/, "")), await _(), k(s, !1);
	});
	async function g() {
		try {
			if (k(h, !0), !(await fetch(`${n()}/activate`, { method: "POST" })).ok) throw Error("Activation failed");
			await _();
		} catch (e) {
			console.error("Failed to activate server:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Activation failed. Check logs.",
				type: "error"
			} }));
		} finally {
			k(h, !1);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (k(r, e.settings.base_url || ""), k(i, e.settings.server_name || ""), k(a, e.settings.has_token || !1), k(o, e.settings.connected || !1), k(m, e.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e);
		}
	}
	async function ee() {
		if (!Y(r).trim()) window.dispatchEvent(new CustomEvent("es-toast", { detail: {
			message: "Server URL is required",
			type: "error"
		} }));
		else try {
			if (k(c, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Y(r),
					server_name: Y(i)
				})
			})).ok) throw Error("Save failed");
			await _(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Settings saved successfully",
				type: "success"
			} }));
		} catch (e) {
			console.error("Failed to save Plex settings:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Failed to save settings.",
				type: "error"
			} }));
		} finally {
			k(c, !1);
		}
	}
	async function te() {
		try {
			k(u, !0);
			let e = await (await fetch(`${n()}/auth/start`, { method: "POST" })).json();
			e?.oauth_url && e?.session_id && (d = e.session_id, window.open(e.oauth_url, "PlexOAuth", "width=600,height=700,menubar=no,status=no"), f = setInterval(async () => {
				try {
					let e = await fetch(`${n()}/auth/poll/${d}`);
					if (!e.ok) {
						e.status === 404 && (clearInterval(f), f = null, k(u, !1), d = null);
						return;
					}
					(await e.json())?.completed && (clearInterval(f), f = null, k(u, !1), d = null, await _(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
						message: "Plex authentication successful!",
						type: "success"
					} })));
				} catch (e) {
					console.error("OAuth poll error:", e);
				}
			}, 3e3));
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e), k(u, !1);
		}
	}
	async function ne() {
		if (d && f) {
			clearInterval(f), f = null;
			try {
				await fetch(`${n()}/auth/cancel/${d}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
			d = null, k(u, !1);
		}
	}
	async function re() {
		try {
			k(l, !0), (await (await fetch(`${n()}/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Y(r) })
			})).json())?.connected ? (window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection successful!",
				type: "success"
			} })), await _()) : window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection failed. Check URL and ensure Plex is running.",
				type: "error"
			} }));
		} catch (e) {
			console.error("Connection test failed:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Test failed with error.",
				type: "error"
			} }));
		} finally {
			k(l, !1);
		}
	}
	var ie = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), qt();
		}
	};
	Qi();
	var ae = ba(), oe = X(ae), se = X(oe), v = Z(X(se), 2), y = X(v), ce = (e) => {
		$(e, la());
	};
	zi(y, (e) => {
		Y(m) && e(ce);
	});
	var le = Z(y, 2), ue = (e) => {
		$(e, ua());
	};
	zi(le, (e) => {
		Y(a) && e(ue);
	});
	var b = Z(le, 2), de = (e) => {
		$(e, da());
	}, x = (e) => {
		$(e, fa());
	};
	zi(b, (e) => {
		Y(o) ? e(de) : Y(a) && e(x, 1);
	}), C(v), C(se);
	var S = Z(se, 2), fe = Fr(S, !0);
	C(oe);
	var me = Z(oe, 2), he = (e) => {
		$(e, pa());
	}, ge = (e) => {
		var t = ya(), n = X(t), o = X(n), s = Z(X(o), 2);
		Wi(s), pe(2), C(o);
		var d = Z(o, 2), f = Z(X(d), 2);
		Wi(f), C(d);
		var p = Z(d, 2), _ = X(p), ie = Fr(_, !0), ae = Z(_, 2), oe = (e) => {
			var t = ma(), n = Fr(t, !0);
			gn((e) => {
				t.disabled = e, ki(n, Y(l) ? "Testing..." : "Test Connection");
			}, [() => (Y(l), Y(r), Cr(() => Y(l) || !Y(r).trim()))]), hi("click", t, re), $(e, t);
		};
		zi(ae, (e) => {
			Y(a) && e(oe);
		});
		var se = Z(ae, 2), v = (e) => {
			var t = ha(), n = Fr(t, !0);
			gn(() => {
				t.disabled = Y(h), ki(n, Y(h) ? "Activating..." : "Activate for Sync");
			}), hi("click", t, g), $(e, t);
		};
		zi(se, (e) => {
			!Y(m) && Y(a) && e(v);
		});
		var y = Z(se, 2), ce = X(y), le = (e) => {
			var t = ga();
			hi("click", t, ne), $(e, t);
		}, ue = (e) => {
			var t = _a();
			hi("click", t, te), $(e, t);
		}, b = (e) => {
			var t = va();
			hi("click", t, te), $(e, t);
		};
		zi(ce, (e) => {
			Y(u) ? e(le) : Y(a) ? e(ue, 1) : e(b, -1);
		}), C(y), C(p), C(n), C(t), gn(() => {
			_.disabled = Y(c), ki(ie, Y(c) ? "Saving..." : "Save Configuration");
		}), Yi(s, () => Y(r), (e) => k(r, e)), Yi(f, () => Y(i), (e) => k(i, e)), hi("click", _, ee), $(e, t);
	};
	return zi(me, (e) => {
		Y(s) ? e(he) : Y(p) || e(ge, 1);
	}), C(ae), gn(() => ki(fe, Y(p) ? "Expand" : "Collapse")), hi("click", S, () => k(p, !Y(p))), $(e, ae), Ye(ie);
}
customElements.define("plex-dashboard-card", ca(Sa, { apiBase: {} }, [], [], { mode: "open" }));
export { Sa as default };
